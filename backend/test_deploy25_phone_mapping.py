"""Deploy 25 checks — Meta custom phone-key mapping + backfill.

The client's Meta forms ask for the number with custom question keys
(work_phone_number, whatsapp_number, phone_/_whatsapp_number), which the
old ingestion ignored, leaving Contact.phone empty while the number sat
in questionnaire_answers. Verifies:
- extract_phone_from_answers(): standard keys win, custom keys are used
  as fallback, junk values are rejected
- process_meta_webhook() stores the custom-key number on the contact
- backfill_contact_phones() repairs existing phoneless contacts from
  their questionnaire answers and is idempotent
Self-cleaning: removes every row it creates.
"""
import sys

from app import create_app
from app.extensions import db
from app.models import Contact, Opportunity, Inquiry, SLAEvent, Note, AuditLog
from app.tasks import extract_phone_from_answers, process_meta_webhook, backfill_contact_phones
from unittest.mock import patch

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


def cleanup():
    contacts = Contact.query.filter(Contact.email.like('%@deploy25.test')).all()
    for c in contacts:
        opps = Opportunity.query.filter_by(contact_id=c.id).all()
        for o in opps:
            SLAEvent.query.filter_by(opportunity_id=o.id).delete()
            Note.query.filter_by(opportunity_id=o.id).delete()
            AuditLog.query.filter_by(table_name='opportunities', record_id=o.id).delete()
            db.session.delete(o)
        Inquiry.query.filter_by(contact_id=c.id).delete()
        db.session.delete(c)
    db.session.commit()


def payload_for(leadgen_id):
    return {
        'object': 'page',
        'entry': [{
            'id': 'PAGE', 'time': 1,
            'changes': [{
                'field': 'leadgen',
                'value': {'form_id': 'F25', 'leadgen_id': leadgen_id,
                          'page_id': 'PAGE', 'created_time': 1},
            }],
        }],
    }


with app.app_context():
    cleanup()

    print('== extract_phone_from_answers ==')
    raw, norm = extract_phone_from_answers({'phone_number': '+8801733333333',
                                            'whatsapp_number': '+8801744444444'})
    check('standard key wins', norm == '+8801733333333')
    raw, norm = extract_phone_from_answers({'whatsapp_number': '01711111111'})
    check('whatsapp fallback + local format normalised',
          raw == '01711111111' and norm == '+8801711111111')
    raw, norm = extract_phone_from_answers({'whatsapp_number': '+8801744444444',
                                            'work_phone_number': '01712222222'})
    check('work_phone preferred over whatsapp', norm == '+8801712222222')
    raw, norm = extract_phone_from_answers({'phone_/_whatsapp_number': '+8801755555555'})
    check('phone_/_whatsapp_number key matched', norm == '+8801755555555')
    raw, norm = extract_phone_from_answers({'whatsapp_number': 'Service'})
    check('junk value rejected', raw == '' and norm is None)
    raw, norm = extract_phone_from_answers({})
    check('empty dict', raw == '' and norm is None)
    raw, norm = extract_phone_from_answers({'full_name': '01716666666'})
    check('non-phone key not used', norm is None)

    print('== process_meta_webhook with custom phone key ==')

    def mock_fetch(app_, leadgen_id):
        return {'id': leadgen_id, 'field_data': [
            {'name': 'full_name', 'values': ['Deploy25 Custom Phone']},
            {'name': 'email', 'values': ['custom@deploy25.test']},
            {'name': 'whatsapp_number', 'values': ['01817777777']},
            {'name': 'your_budget?', 'values': ['30-40 lakh']},
        ]}

    with patch('app.tasks._fetch_meta_lead', side_effect=mock_fetch):
        n = process_meta_webhook(payload_for('D25_LEAD_1'), app)
    check('one lead processed', n == 1)
    c = Contact.query.filter_by(email='custom@deploy25.test').first()
    check('contact created', c is not None)
    check('phone filled from whatsapp_number',
          c is not None and c.phone_normalized == '+8801817777777' and c.phone_raw == '01817777777')
    opp = Opportunity.query.filter_by(contact_id=c.id).first() if c else None
    check('questionnaire kept custom answers',
          opp is not None and (opp.questionnaire_answers or {}).get('your_budget?') == '30-40 lakh')

    print('== backfill_contact_phones ==')
    bc = Contact(full_name='Deploy25 Backfill', email='backfill@deploy25.test',
                 phone_raw='', phone_normalized=None, source='Meta Lead Ads',
                 facebook_lead_id='D25_BF_1')
    db.session.add(bc)
    db.session.flush()
    bo = Opportunity(contact_id=bc.id, pipeline_stage='NEW',
                     questionnaire_answers={'whatsapp_number': '+8801788888888',
                                            'company_name': 'Test Co'})
    db.session.add(bo)
    junk = Contact(full_name='Deploy25 Junk', email='junk@deploy25.test',
                   phone_raw='', phone_normalized=None, source='Meta Lead Ads',
                   facebook_lead_id='D25_BF_2')
    db.session.add(junk)
    db.session.flush()
    jo = Opportunity(contact_id=junk.id, pipeline_stage='NEW',
                     questionnaire_answers={'whatsapp_number': 'call me maybe'})
    db.session.add(jo)
    db.session.commit()

    result = backfill_contact_phones(app)
    check('backfill filled the valid one', result['filled'] >= 1)
    bc2 = Contact.query.filter_by(email='backfill@deploy25.test').first()
    check('backfilled phone stored',
          bc2.phone_normalized == '+8801788888888' and bc2.phone_raw == '+8801788888888')
    junk2 = Contact.query.filter_by(email='junk@deploy25.test').first()
    check('junk answers left phoneless', not junk2.phone_normalized and not junk2.phone_raw)
    result2 = backfill_contact_phones(app)
    bc3 = Contact.query.filter_by(email='backfill@deploy25.test').first()
    check('idempotent (phone unchanged, not re-filled)',
          bc3.phone_normalized == '+8801788888888')

    cleanup()
    print(f'\n{passed} passed, {failed} failed')
    sys.exit(1 if failed else 0)
