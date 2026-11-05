"""Targeted tests for deploy 31 (2026-11-05): instant lead pull on connect.

User requirement: "reconnect korle sathe sathe asbe" — after a successful
Facebook (re)connect, waiting Meta leads must flow into the CRM
immediately instead of waiting for the next 5-minute scheduler poll.
facebook_oauth_callback now kicks poll_facebook_leads() in a daemon
thread right after the token + forms are stored, and the success page
tells the admin the pull has started.

The Graph calls are monkeypatched — no network. Run from backend/:
    venv/bin/python test_deploy31_connect_poll.py
"""
import os
import sys
import time

os.environ['FLASK_CONFIG'] = 'testing'
os.environ['DISABLE_SCHEDULER'] = 'true'
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models import SystemSetting
import app.tasks as tasks_module
from app.blueprints.webhooks import facebook as fb

app = create_app('testing')
app.config['TESTING'] = True
client = app.test_client()

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


class FakeResp:
    def json(self):
        return {'access_token': 'fake-user-token'}


def main():
    poll_calls = []

    def fake_poll(app=None):
        poll_calls.append(app)
        return {'forms_checked': 0, 'new_leads': 0}

    with app.app_context():
        db.create_all()
        SystemSetting.set('facebook_app_id', '123456')
        SystemSetting.set('facebook_app_secret', 'shh')
        SystemSetting.set('oauth_state', 'state-xyz')
        SystemSetting.set('facebook_page_id', '')
        db.session.commit()

    orig_get = fb.requests.get
    orig_pages = fb._fetch_user_pages
    orig_sub = fb._subscribe_page_webhooks
    orig_sync = fb._sync_lead_forms
    orig_poll = tasks_module.poll_facebook_leads
    fb.requests.get = lambda *a, **k: FakeResp()
    fb._fetch_user_pages = lambda tok: ([{'id': 'pg1', 'name': 'Test Page', 'access_token': 'ptok'}], 'dbg')
    fb._subscribe_page_webhooks = lambda pid, ptok: 'Subscribed.'
    fb._sync_lead_forms = lambda pid, ptok: 'Forms synced.'
    tasks_module.poll_facebook_leads = fake_poll
    try:
        r = client.get('/api/webhooks/facebook/oauth/callback?code=abc&state=state-xyz')
        body = r.get_data(as_text=True)
        check('callback succeeds', r.status_code == 200, f'status={r.status_code}')
        check('success page announces the immediate pull',
              'এখনই টানা শুরু হয়েছে' in body)
        # the poll runs in a daemon thread — give it a moment
        deadline = time.time() + 3
        while not poll_calls and time.time() < deadline:
            time.sleep(0.05)
        check('poll_facebook_leads kicked immediately', len(poll_calls) == 1,
              f'calls={len(poll_calls)}')
        check('poll received the app object', bool(poll_calls and poll_calls[0] is not None))
        with app.app_context():
            check('page stored as live connection',
                  SystemSetting.get('facebook_page_id') == 'pg1'
                  and SystemSetting.get('facebook_connection_mode') == 'live'
                  and SystemSetting.get('facebook_page_access_token') == 'ptok')
    finally:
        fb.requests.get = orig_get
        fb._fetch_user_pages = orig_pages
        fb._subscribe_page_webhooks = orig_sub
        fb._sync_lead_forms = orig_sync
        tasks_module.poll_facebook_leads = orig_poll

    passed = sum(1 for _, ok in CHECKS if ok)
    print(f"\n{passed}/{len(CHECKS)} checks passed")
    sys.exit(0 if passed == len(CHECKS) else 1)


if __name__ == '__main__':
    main()
