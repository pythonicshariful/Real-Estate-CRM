"""
Smoke test for Southeast Landmark CRM (local dev, SQLite).
Runs a real end-to-end flow against the Flask test client.

Usage:  ../.venv/bin/python smoke_test.py
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DISABLE_SCHEDULER', 'True')

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db

app = create_app('development')
app.config['RATELIMIT_ENABLED'] = False
# flask-limiter reads RATELIMIT_ENABLED at init_app() time, so force it off
try:
    from app.extensions import limiter
    limiter.enabled = False
except Exception:
    pass

results = []


def record(module, name, method, path, resp, expected=(200, 201)):
    ok = resp.status_code in expected
    body = ''
    try:
        j = resp.get_json()
        if isinstance(j, dict):
            if j.get('status') == 'error' or 'msg' in j:
                body = str(j.get('message') or j.get('msg'))[:90]
            else:
                keys = list(j.keys())[:4]
                body = f"keys={keys}"
    except Exception:
        body = resp.data[:60].decode('utf-8', 'ignore').replace('\n', ' ')

    results.append({
        'module': module, 'name': name, 'method': method, 'path': path,
        'code': resp.status_code, 'ok': ok, 'note': body
    })
    flag = 'PASS' if ok else 'FAIL'
    print(f"[{flag}] {resp.status_code}  {method:5} {path:52} {body}")
    return resp


def call(client, module, name, method, path, expected=(200, 201), **kw):
    fn = getattr(client, method.lower())
    try:
        resp = fn(path, **kw)
    except Exception as e:
        results.append({'module': module, 'name': name, 'method': method, 'path': path,
                        'code': 'EXC', 'ok': False, 'note': f'{type(e).__name__}: {e}'})
        print(f"[FAIL] EXC   {method:5} {path:52} {type(e).__name__}: {e}")
        traceback.print_exc(limit=3)
        return None
    return record(module, name, method, path, resp, expected)


print('=' * 110)
print('SOUTHEAST LANDMARK CRM — SMOKE TEST')
print('=' * 110)

# ---------------------------------------------------------------- public
with app.test_client() as c:
    print('\n--- PUBLIC ---')
    call(c, 'core', 'health', 'GET', '/health')
    call(c, 'core', 'root page', 'GET', '/')
    call(c, 'core', 'login page', 'GET', '/index.html')
    call(c, 'core', 'dashboard page', 'GET', '/dashboard.html')
    call(c, 'core', 'leads page', 'GET', '/leads.html')
    call(c, 'core', 'assets css', 'GET', '/assets/css/main.css')
    call(c, 'core', 'auth required 401', 'GET', '/api/auth/me', expected=(401,))

    print('\n--- AUTH ---')
    r = call(c, 'auth', 'login bad password', 'POST', '/api/auth/login',
             expected=(401,), json={'email': 'admin@southeast.com', 'password': 'wrong'})
    r = call(c, 'auth', 'login admin', 'POST', '/api/auth/login',
             json={'email': 'admin@southeast.com', 'password': 'Admin@123'})
    admin_tok = r.get_json()['access_token']
    r = call(c, 'auth', 'login lead owner', 'POST', '/api/auth/login',
             json={'email': 'john@southeast.com', 'password': 'John@123'})
    owner_tok = r.get_json()['access_token']
    owner_id = None

    H = lambda t: {'Authorization': f'Bearer {t}'}
    call(c, 'auth', 'me', 'GET', '/api/auth/me', headers=H(admin_tok))
    me = c.get('/api/auth/me', headers=H(owner_tok)).get_json()
    owner_id = (me.get('user') or me).get('id') if isinstance(me, dict) else None
    call(c, 'auth', 'me stats', 'GET', '/api/auth/me/stats', headers=H(admin_tok))

    A = H(admin_tok)
    O = H(owner_tok)

    # ------------------------------------------------------------ dashboard
    print('\n--- DASHBOARD / REPORTS ---')
    call(c, 'dashboard', 'stats', 'GET', '/api/dashboard/stats', headers=A)
    call(c, 'dashboard', 'badges', 'GET', '/api/dashboard/badges', headers=A)
    call(c, 'dashboard', 'funnel', 'GET', '/api/dashboard/funnel', headers=A)
    call(c, 'dashboard', 'recent activity', 'GET', '/api/dashboard/recent-activity', headers=A)
    call(c, 'dashboard', 'sla overdue', 'GET', '/api/dashboard/sla-overdue', headers=A)
    call(c, 'reports', 'kpis', 'GET', '/api/reports/kpis', headers=A)
    call(c, 'reports', 'charts', 'GET', '/api/reports/charts', headers=A)
    call(c, 'reports', 'sales summary', 'GET', '/api/reports/sales-manager-summary', headers=A)
    call(c, 'reports', 'export leads csv', 'GET', '/api/reports/export/leads', headers=A)

    # ------------------------------------------------------------ leads CRUD
    print('\n--- LEADS ---')
    call(c, 'leads', 'list', 'GET', '/api/leads/', headers=A)
    call(c, 'leads', 'list (owner scoped)', 'GET', '/api/leads/', headers=O)
    call(c, 'leads', 'sample csv', 'GET', '/api/leads/sample-csv', headers=A)
    call(c, 'leads', 'import template', 'GET', '/api/leads/import/template', headers=A)

    r = call(c, 'leads', 'create', 'POST', '/api/leads/', headers=A, json={
        'full_name': 'Test Buyer One',
        'phone': '+8801712345678',
        'email': 'testbuyer1@example.com',
        'source': 'Smoke Test',
        'project_interest': 'Elite Society',
        'budget_min': 5000000,
        'budget_max': 8000000,
    })
    lead_id = (r.get_json() or {}).get('lead', {}).get('id') if r is not None else None
    if not lead_id:
        lead_id = (r.get_json() or {}).get('id') if r is not None else None
    print(f'        -> created lead_id={lead_id}')

    # duplicate detection should kick in
    call(c, 'leads', 'duplicate blocked (409)', 'POST', '/api/leads/', headers=A,
         expected=(409,), json={'full_name': 'Test Buyer One', 'phone': '+8801712345678'})
    call(c, 'leads', 'duplicate check', 'GET', '/api/leads/check-duplicate?phone=%2B8801712345678', headers=A)
    call(c, 'leads', 'duplicate count', 'GET', '/api/leads/duplicate-count', headers=A)

    # second lead via owner (different phone)
    r = call(c, 'leads', 'create (owner)', 'POST', '/api/leads/', headers=O, json={
        'full_name': 'Test Buyer Two',
        'phone': '+8801987654321',
        'email': 'testbuyer2@example.com',
        'source': 'Smoke Test',
    })
    lead2_id = (r.get_json() or {}).get('lead', {}).get('id') if r is not None else None

    r = call(c, 'leads', 'create 2 more', 'POST', '/api/leads/', headers=A, json={
        'full_name': 'Test Buyer Three', 'phone': '+8801911111111',
        'email': 'testbuyer3@example.com', 'source': 'Smoke Test'})
    lead3_id = (r.get_json() or {}).get('lead', {}).get('id') if r is not None else None

    if lead_id:
        call(c, 'leads', 'detail', 'GET', f'/api/leads/{lead_id}', headers=A)
        call(c, 'leads', 'profile', 'GET', f'/api/leads/{lead_id}/profile', headers=A)
        call(c, 'leads', 'update', 'PUT', f'/api/leads/{lead_id}', headers=A, json={
            'full_name': 'Test Buyer One (updated)', 'budget_min': 6000000})
        call(c, 'leads', 'temperature', 'PUT', f'/api/leads/{lead_id}/temperature', headers=A,
             json={'temperature': 'HOT'})
        call(c, 'leads', 'star', 'PUT', f'/api/leads/{lead_id}/star', headers=A, json={'is_starred': True})
        call(c, 'leads', 'add note', 'POST', f'/api/leads/{lead_id}/notes', headers=A,
             json={'text': 'Called buyer, interested in 3-bed unit.'})
        call(c, 'leads', 'questionnaire get', 'GET', f'/api/leads/{lead_id}/questionnaire', headers=A)
        call(c, 'leads', 'add call log', 'POST', f'/api/leads/{lead_id}/calls', headers=A, json={
            'call_type': 'OUTBOUND', 'connected': True,
            'outcome': 'CONNECTED', 'duration_band': 'ONE_TO_3MIN',
            'notes': 'Smoke test call'})
        call(c, 'leads', 'appointments list', 'GET', f'/api/leads/{lead_id}/appointments', headers=A)
        call(c, 'leads', 'objections', 'GET', f'/api/leads/{lead_id}/objections', headers=A)
        call(c, 'leads', 'reservations', 'GET', f'/api/leads/{lead_id}/reservations', headers=A)
        call(c, 'leads', 'appointment create', 'POST', f'/api/leads/{lead_id}/appointments', headers=A, json={
            'title': 'Site visit', 'appointment_datetime': '2026-11-05T11:00:00'})
        call(c, 'leads', 'coaching', 'GET', '/api/leads/coaching', headers=A)
        call(c, 'leads', 'bulk assign', 'POST', '/api/leads/bulk-assign', headers=A,
             json={'lead_ids': [lead_id], 'owner_id': owner_id})
        if owner_id:
            call(c, 'leads', 'reassign', 'PUT', f'/api/leads/{lead_id}/reassign', headers=A,
                 json={'owner_id': owner_id})

    # ------------------------------------------------------------ contacts
    print('\n--- CONTACTS ---')
    call(c, 'contacts', 'list', 'GET', '/api/contacts/', headers=A)
    r = call(c, 'contacts', 'create', 'POST', '/api/contacts/', headers=A, json={
        'full_name': 'Contact Person A', 'phone': '+8801777000111', 'email': 'cpa@example.com',
        'source': 'Smoke Test'})
    cid = (r.get_json() or {}).get('id') if r is not None else None
    listj = c.get('/api/contacts/', headers=A).get_json()
    if not cid and isinstance(listj, list) and listj:
        cid = listj[0].get('id')
    if cid:
        call(c, 'contacts', 'detail', 'GET', f'/api/contacts/{cid}', headers=A)
        call(c, 'contacts', 'inquiries', 'GET', f'/api/contacts/{cid}/inquiries', headers=A)
        call(c, 'contacts', 'opportunities', 'GET', f'/api/contacts/{cid}/opportunities', headers=A)

    # ------------------------------------------------------------ projects
    print('\n--- PROJECTS ---')
    r = call(c, 'projects', 'list', 'GET', '/api/projects/', headers=A)
    pl = r.get_json()
    pid = pl[0]['id'] if isinstance(pl, list) and pl else None
    r = call(c, 'projects', 'create', 'POST', '/api/projects/', headers=A, json={
        'name': 'Smoke Test Tower', 'code': 'SMOKE-01', 'location': 'Dhaka',
        'total_units': 50, 'price_per_sqft': 9000})
    if r is not None and isinstance(r.get_json(), dict):
        pid = r.get_json().get('id') or pid
    if pid:
        call(c, 'projects', 'phases', 'GET', f'/api/projects/{pid}/phases', headers=A)
        r = call(c, 'projects', 'create phase', 'POST', f'/api/projects/{pid}/phases', headers=A,
                 json={'name': 'Phase 1'})
        phase_id = (r.get_json() or {}).get('id') if r is not None else None
        call(c, 'projects', 'plots', 'GET', f'/api/projects/{pid}/plots', headers=A)
        call(c, 'projects', 'create plot', 'POST', f'/api/projects/{pid}/plots', headers=A,
             json={'plot_number': 'A-101', 'size_katha': 5, 'rate_per_katha': 1600000,
                  'total_price': 8000000})
        if phase_id:
            call(c, 'projects', 'blocks', 'GET', f'/api/projects/phases/{phase_id}/blocks', headers=A)

    # ------------------------------------------------------------ team
    print('\n--- TEAM / RBAC ---')
    call(c, 'team', 'lead owners', 'GET', '/api/team/lead-owners', headers=A)
    call(c, 'team', 'users', 'GET', '/api/team/users', headers=A)
    call(c, 'team', 'members', 'GET', '/api/team/members', headers=A)
    if owner_id:
        call(c, 'team', 'owner stats', 'GET', f'/api/team/lead-owners/{owner_id}/stats', headers=A)
        call(c, 'team', 'owner activities', 'GET', f'/api/team/lead-owners/{owner_id}/activities', headers=A)
    call(c, 'rbac', 'owner blocked from team (403)', 'GET', '/api/team/lead-owners', headers=O,
         expected=(403,))
    call(c, 'rbac', 'owner blocked from settings (403)', 'GET', '/api/settings/general', headers=O,
         expected=(403,))

    # ------------------------------------------------------------ tasks/events/notes
    print('\n--- TASKS / EVENTS / NOTES / MESSAGES / TICKETS ---')
    call(c, 'tasks', 'list', 'GET', '/api/tasks/', headers=A)
    r = call(c, 'tasks', 'create', 'POST', '/api/tasks/', headers=A, json={
        'title': 'Follow up with Test Buyer One', 'priority': 'HIGH',
        'due_date': '2026-11-01'})
    tid = (r.get_json() or {}).get('id') if r is not None else None
    if tid:
        call(c, 'tasks', 'update', 'PUT', f'/api/tasks/{tid}', headers=A, json={'status': 'COMPLETED'})

    call(c, 'events', 'list', 'GET', '/api/events/', headers=A)
    r = call(c, 'events', 'create', 'POST', '/api/events/', headers=A, json={
        'title': 'Team standup', 'start_datetime': '2026-11-02T10:00:00',
        'end_datetime': '2026-11-02T11:00:00'})
    eid = (r.get_json() or {}).get('id') if r is not None else None
    if eid:
        call(c, 'events', 'detail', 'GET', f'/api/events/{eid}', headers=A)
        call(c, 'events', 'update', 'PUT', f'/api/events/{eid}', headers=A, json={'title': 'Team standup v2'})

    call(c, 'notes', 'list', 'GET', '/api/notes/', headers=A)
    r = call(c, 'notes', 'create', 'POST', '/api/notes/', headers=A, json={'content': 'Smoke test note'})
    nid = (r.get_json() or {}).get('id') if r is not None else None
    if nid:
        call(c, 'notes', 'update', 'PUT', f'/api/notes/{nid}', headers=A, json={'content': 'updated'})

    call(c, 'messages', 'list', 'GET', '/api/messages/', headers=A)
    call(c, 'messages', 'unread count', 'GET', '/api/messages/unread-count', headers=A)
    if owner_id:
        call(c, 'messages', 'send', 'POST', '/api/messages/', headers=A,
             json={'recipient_id': owner_id, 'body': 'Hello from smoke test'})
        call(c, 'messages', 'conversation', 'GET', f'/api/messages/conversation/{owner_id}', headers=A)

    call(c, 'tickets', 'list', 'GET', '/api/tickets/', headers=A)
    call(c, 'tickets', 'create', 'POST', '/api/tickets/', headers=A, json={
        'subject': 'Smoke test ticket', 'description': 'Something is broken', 'priority': 'MEDIUM'})

    # ------------------------------------------------------------ finance / expenses
    print('\n--- FINANCE / EXPENSES ---')
    call(c, 'finance', 'invoices', 'GET', '/api/finance/invoices/', headers=A)
    call(c, 'finance', 'contracts', 'GET', '/api/finance/contracts/', headers=A)
    call(c, 'finance', 'orders', 'GET', '/api/finance/orders/', headers=A)
    call(c, 'finance', 'items', 'GET', '/api/finance/items/', headers=A)
    call(c, 'expenses', 'list', 'GET', '/api/expenses/', headers=A)
    call(c, 'expenses', 'summary', 'GET', '/api/expenses/summary', headers=A)

    # ------------------------------------------------------------ settings / security / misc
    print('\n--- SETTINGS / SECURITY / MISC ---')
    for p in ['/api/settings/general', '/api/settings/sla', '/api/settings/system',
              '/api/settings/roles', '/api/settings/branding', '/api/settings/meta-webhook',
              '/api/settings/questionnaire', '/api/settings/activity-labels',
              '/api/settings/email-templates', '/api/settings/b2-storage',
              '/api/settings/quick_notes']:
        call(c, 'settings', p.rsplit('/', 1)[-1], 'GET', p, headers=A)

    call(c, 'security', 'audit log', 'GET', '/api/security/audit-log', headers=A)
    call(c, 'security', 'recording downloads', 'GET', '/api/security/recording-downloads', headers=A)
    call(c, 'help', 'articles', 'GET', '/api/help/articles', headers=A)
    call(c, 'prospects', 'proposals', 'GET', '/api/prospects/proposals', headers=A)
    call(c, 'prospects', 'estimates', 'GET', '/api/prospects/estimates', headers=A)
    call(c, 'webhooks', 'meta verify', 'GET', '/api/webhooks/meta?hub.mode=subscribe&hub.verify_token=sl_crm_secure_webhook_token_2025&hub.challenge=TEST123', headers=A)
    call(c, 'webhooks', 'meta status', 'GET', '/api/webhooks/meta/status', headers=A)

    # ------------------------------------------------------------ delete lifecycle
    print('\n--- DELETE LIFECYCLE ---')
    if lead3_id:
        call(c, 'leads', 'delete', 'DELETE', f'/api/leads/{lead3_id}', headers=A)
    if tid:
        call(c, 'tasks', 'delete', 'DELETE', f'/api/tasks/{tid}', headers=A)
    if nid:
        call(c, 'notes', 'delete', 'DELETE', f'/api/notes/{nid}', headers=A)

    print('\n--- AUTH LOGOUT ---')
    call(c, 'auth', 'logout', 'POST', '/api/auth/logout', headers=A)
    call(c, 'auth', 'token revoked (401)', 'GET', '/api/auth/me', headers=A, expected=(401,))

# ---------------------------------------------------------------- summary
print('\n' + '=' * 110)
total = len(results)
passed = sum(1 for r in results if r['ok'])
failed = [r for r in results if not r['ok']]
print(f'TOTAL: {total}   PASSED: {passed}   FAILED: {len(failed)}   '
      f'SUCCESS RATE: {passed / total * 100:.1f}%')
print('=' * 110)

if failed:
    print('\nFAILURES BY MODULE:')
    by_mod = {}
    for f in failed:
        by_mod.setdefault(f['module'], []).append(f)
    for mod, items in sorted(by_mod.items()):
        print(f'\n  [{mod}] {len(items)} failure(s)')
        for f in items:
            print(f"    - {f['method']:6} {f['path']:55} -> {f['code']}  {f['note']}")

with open('smoke_test_results.json', 'w') as fh:
    json.dump({'total': total, 'passed': passed, 'failed': len(failed), 'results': results}, fh, indent=2)
print('\nDetailed results written to smoke_test_results.json')
