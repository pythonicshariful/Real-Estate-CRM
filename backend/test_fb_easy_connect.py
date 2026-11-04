"""Tests for the Easy Connect OAuth improvements (deploy 19).

Covers:
- _fetch_user_pages: direct /me/accounts hit returns pages immediately.
- _fetch_user_pages: empty /me/accounts falls back to Business-owned and
  client pages; pages without an access_token and duplicates are dropped.
- _fetch_user_pages: a Graph error on /me/accounts is captured in the debug
  trail (no exception) and the result is empty when nothing is found.
- OAuth callback with no pages anywhere returns the friendly Bangla
  failure page (title + retry guidance), not the old English dead-end.
- OAuth callback success path still connects to the first page found.

Run: venv/bin/python test_fb_easy_connect.py  (from backend/)
Uses the in-memory testing config; all Facebook calls are mocked.
"""
import os
import sys
from unittest.mock import patch

os.environ['FLASK_CONFIG'] = 'testing'
os.environ['DISABLE_SCHEDULER'] = 'true'
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models import SystemSetting
import app.blueprints.webhooks.facebook as fb

app = create_app('testing')
app.config['TESTING'] = True
client = app.test_client()

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, ok, detail))
    print(('PASS' if ok else 'FAIL'), '-', name, detail if not ok else '')


class Resp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def fake_get_factory(routes):
    """routes: list of (url_substring, payload) matched in order."""
    def _get(url, params=None, timeout=None):
        for needle, payload in routes:
            if needle in url:
                return Resp(payload)
        raise AssertionError(f'unmocked GET {url}')
    return _get


with app.app_context():
    db.create_all()

    # --- Case A: direct pages -------------------------------------------
    routes_a = [('/me/accounts', {'data': [
        {'id': '111', 'name': 'Direct Page', 'access_token': 'tok-a'},
    ]})]
    with patch.object(fb.requests, 'get', side_effect=fake_get_factory(routes_a)):
        pages, debug = fb._fetch_user_pages('user-token')
    check('A: direct /me/accounts page returned',
          len(pages) == 1 and pages[0]['id'] == '111' and debug.get('me_accounts_count') == 1,
          f'pages={pages} debug={debug}')

    # --- Case B: business fallback --------------------------------------
    routes_b = [
        ('/me/accounts', {'data': []}),
        ('/me/businesses', {'data': [{'id': 'biz1', 'name': 'Biz One'}]}),
        ('/biz1/owned_pages', {'data': [
            {'id': '222', 'name': 'Owned Page', 'access_token': 'tok-b'},
            {'id': '333', 'name': 'No Token Page'},
        ]}),
        ('/biz1/client_pages', {'data': [
            {'id': '222', 'name': 'Owned Page', 'access_token': 'tok-b'},
            {'id': '444', 'name': 'Client Page', 'access_token': 'tok-c'},
        ]}),
    ]
    with patch.object(fb.requests, 'get', side_effect=fake_get_factory(routes_b)):
        pages, debug = fb._fetch_user_pages('user-token')
    ids = sorted(p['id'] for p in pages)
    check('B: fallback merges owned+client, drops tokenless + dupes',
          ids == ['222', '444'] and debug.get('business_pages_count') == 2,
          f'ids={ids} debug={debug}')

    # --- Case C: graph error + nothing anywhere --------------------------
    routes_c = [
        ('/me/accounts', {'error': {'message': 'Invalid OAuth access token.', 'code': 190}}),
        ('/me/businesses', {'data': []}),
    ]
    with patch.object(fb.requests, 'get', side_effect=fake_get_factory(routes_c)):
        pages, debug = fb._fetch_user_pages('user-token')
    check('C: error captured in debug, empty result, no exception',
          pages == [] and 'Invalid OAuth' in str(debug.get('me_accounts_error')),
          f'pages={pages} debug={debug}')

    # --- Case D: callback with no pages -> friendly Bangla page ----------
    SystemSetting.set('facebook_app_id', '1234567890')
    SystemSetting.set('facebook_app_secret', 'test-secret')
    SystemSetting.set('oauth_state', 'state-xyz')

    def callback_get(url, params=None, timeout=None):
        if 'oauth/access_token' in url:
            return Resp({'access_token': 'short-user-token'})
        if '/me/accounts' in url:
            return Resp({'data': []})
        if '/me/businesses' in url:
            return Resp({'data': []})
        raise AssertionError(f'unmocked GET {url}')

    with patch.object(fb.requests, 'get', side_effect=callback_get):
        resp = client.get('/api/webhooks/facebook/oauth/callback?code=abc&state=state-xyz')
    body = resp.get_data(as_text=True)
    check('D: no-pages callback is the Bangla guidance page',
          resp.status_code == 400 and 'কানেক্ট হয়নি' in body and 'Page-টা টিক দিন' in body,
          f'status={resp.status_code}')

    # --- Case E: callback success via business fallback ------------------
    SystemSetting.set('oauth_state', 'state-xyz')

    def callback_get_e(url, params=None, timeout=None):
        if 'oauth/access_token' in url:
            return Resp({'access_token': 'short-user-token'})
        if '/me/accounts' in url:
            return Resp({'data': []})
        if '/me/businesses' in url:
            return Resp({'data': [{'id': 'biz9', 'name': 'Biz Nine'}]})
        if '/biz9/owned_pages' in url:
            return Resp({'data': [{'id': '999', 'name': 'Biz Page', 'access_token': 'page-tok'}]})
        if '/biz9/client_pages' in url:
            return Resp({'data': []})
        raise AssertionError(f'unmocked GET {url}')

    with patch.object(fb.requests, 'get', side_effect=callback_get_e), \
         patch.object(fb, '_subscribe_page_webhooks', return_value='Page subscribed to lead webhooks.'), \
         patch.object(fb, '_sync_lead_forms', return_value='Found 0 lead form(s).'):
        resp = client.get('/api/webhooks/facebook/oauth/callback?code=abc&state=state-xyz')
    body = resp.get_data(as_text=True)
    check('E: business-fallback page connects successfully',
          resp.status_code == 200 and 'Biz Page' in body
          and SystemSetting.get('facebook_page_id') == '999'
          and SystemSetting.get('facebook_connection_mode') == 'live',
          f'status={resp.status_code} page={SystemSetting.get("facebook_page_id")}')

failed = [c for c in CHECKS if not c[1]]
print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
sys.exit(1 if failed else 0)
