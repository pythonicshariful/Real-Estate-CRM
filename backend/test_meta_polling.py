"""Deploy 23 checks — Meta lead polling (Graph API fallback).

Verifies poll_facebook_leads():
- pulls leads listed on a form and ingests them via the webhook path
- advances the per-form watermark and feeds nothing twice
- skips leads already ingested by a real webhook (facebook_lead_id)
- is a no-op unless a Page is connected in live mode
Self-cleaning: removes every row and setting it creates.
"""
import json
import sys
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import SystemSetting, Contact, Inquiry, Opportunity
from app.tasks import poll_facebook_leads

app = create_app()

passed = 0
failed = 0


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f'  PASS {name}')
    else:
        failed += 1
        print(f'  FAIL {name}')


LEAD_DETAILS = {
    'L1': [
        {'name': 'full_name', 'values': ['Poll Test Lead One']},
        {'name': 'email', 'values': ['poll.one@example.com']},
        {'name': 'phone_number', 'values': ['+8801999111001']},
        {'name': 'which_project_are_you_interested_in?', 'values': ['Southeast City']},
    ],
    'L2': [
        {'name': 'full_name', 'values': ['Poll Test Lead Two']},
        {'name': 'email', 'values': ['poll.two@example.com']},
        {'name': 'phone_number', 'values': ['+8801999111002']},
    ],
    'L3': [
        {'name': 'full_name', 'values': ['Poll Test Lead Three']},
        {'name': 'email', 'values': ['poll.three@example.com']},
        {'name': 'phone_number', 'values': ['+8801999111003']},
    ],
}

FORM_LEADS = {
    'FORM1': [
        {'id': 'L2', 'created_time': '2026-11-05T06:00:00+0000'},
        {'id': 'L1', 'created_time': '2026-11-05T05:00:00+0000'},
    ],
    'FORM2': [
        {'id': 'L3', 'created_time': '2026-11-05T07:00:00+0000'},
    ],
}


class FakeResp:
    def __init__(self, payload):
        self._payload = payload
        self.ok = True
        self.status_code = 200

    def json(self):
        return self._payload


def fake_get(url, params=None, timeout=None):
    for form_id, leads in FORM_LEADS.items():
        if url.endswith(f'/{form_id}/leads'):
            return FakeResp({'data': leads})
    return FakeResp({'data': []})


def fake_fetch_meta_lead(app_, leadgen_id):
    return {'id': leadgen_id, 'field_data': LEAD_DETAILS[leadgen_id]}


def set_settings(**kw):
    for k, v in kw.items():
        SystemSetting.set(k, v)
    db.session.commit()


def cleanup():
    for lid in ('L1', 'L2', 'L3'):
        c = Contact.query.filter_by(facebook_lead_id=lid).first()
        if c:
            Opportunity.query.filter_by(contact_id=c.id).delete()
            Inquiry.query.filter_by(contact_id=c.id).delete()
            db.session.delete(c)
    for em in ('poll.one@example.com', 'poll.two@example.com', 'poll.three@example.com'):
        c = Contact.query.filter_by(email=em).first()
        if c:
            Opportunity.query.filter_by(contact_id=c.id).delete()
            Inquiry.query.filter_by(contact_id=c.id).delete()
            db.session.delete(c)
    db.session.commit()
    set_settings(facebook_page_access_token='', facebook_page_id='',
                 facebook_connection_mode='', facebook_lead_forms_json='',
                 facebook_poll_state_json='')


def main():
    with app.app_context():
        cleanup()

        # --- live connection with two forms -------------------------------
        set_settings(
            facebook_page_access_token='TESTTOKEN',
            facebook_page_id='PAGE1',
            facebook_connection_mode='live',
            facebook_lead_forms_json=json.dumps([
                {'id': 'FORM1', 'name': 'Seminar', 'status': 'ACTIVE'},
                {'id': 'FORM2', 'name': 'Other', 'status': 'ACTIVE'},
            ]),
            facebook_poll_state_json='',
        )
        # L3 was already delivered by a real webhook earlier.
        pre = Contact(full_name='Poll Test Lead Three', email='poll.three@example.com',
                      phone_raw='+8801999111003', source='Meta Lead Ads',
                      facebook_lead_id='L3', consent_given=True)
        db.session.add(pre)
        db.session.commit()

        with patch('requests.get', side_effect=fake_get), \
             patch('app.tasks._fetch_meta_lead', side_effect=fake_fetch_meta_lead):
            s1 = poll_facebook_leads(app=app)
        check('first poll ingests the 2 new FORM1 leads', s1['new_leads'] == 2)
        check('first poll checks both forms', s1['forms_checked'] == 2)
        check('webhook-delivered L3 skipped', s1['skipped_existing'] == 1)

        c1 = Contact.query.filter_by(facebook_lead_id='L1').first()
        c2 = Contact.query.filter_by(facebook_lead_id='L2').first()
        check('L1 contact created', c1 is not None and c1.full_name == 'Poll Test Lead One')
        check('L2 contact created', c2 is not None)
        opp1 = Opportunity.query.filter_by(contact_id=c1.id).first() if c1 else None
        check('L1 opportunity created', opp1 is not None)
        check('L1 custom question stored on the opportunity',
              bool(opp1) and (opp1.questionnaire_answers or {}).get(
                  'which_project_are_you_interested_in?') == 'Southeast City')

        state = json.loads(SystemSetting.get('facebook_poll_state_json') or '{}')
        check('FORM1 watermark advanced to newest lead',
              state.get('FORM1') == '2026-11-05T06:00:00+0000')

        # --- second poll: nothing new --------------------------------------
        with patch('requests.get', side_effect=fake_get), \
             patch('app.tasks._fetch_meta_lead', side_effect=fake_fetch_meta_lead):
            s2 = poll_facebook_leads(app=app)
        check('second poll ingests nothing', s2['new_leads'] == 0)
        n_inq = Inquiry.query.filter_by(contact_id=c1.id).count() if c1 else -1
        check('no duplicate inquiry for L1', n_inq == 1)

        # --- not live: no-op -------------------------------------------------
        set_settings(facebook_connection_mode='demo')
        with patch('requests.get', side_effect=fake_get) as mock_get:
            s3 = poll_facebook_leads(app=app)
        check('demo mode poll is a no-op', s3['new_leads'] == 0 and mock_get.call_count == 0)

        cleanup()
        print(f'\n{passed} passed, {failed} failed')
        return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
