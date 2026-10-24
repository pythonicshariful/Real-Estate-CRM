"""Test: Event↔Lead linkage, owner colours, RBAC visibility, Facebook connect."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DISABLE_SCHEDULER', 'True')
from dotenv import load_dotenv; load_dotenv()

from app import create_app
from app.extensions import db, limiter

app = create_app('development')
limiter.enabled = False

P = F = 0
def chk(name, ok, extra=''):
    global P, F
    if ok: P += 1
    else: F += 1
    print(f"{'[PASS]' if ok else '[FAIL]'} {name}" + (f" — {extra}" if extra else ''))

with app.test_client() as c:
    # ── login
    adm = c.post('/api/auth/login', json={'email':'admin@southeast.com','password':'Admin@123'}).get_json()
    joh = c.post('/api/auth/login', json={'email':'john@southeast.com','password':'John@123'}).get_json()
    sar = c.post('/api/auth/login', json={'email':'sarah@southeast.com','password':'Sarah@123'}).get_json()
    A = {'Authorization': f"Bearer {adm['access_token']}"}
    J = {'Authorization': f"Bearer {joh['access_token']}"}
    S = {'Authorization': f"Bearer {sar['access_token']}"}
    print(f"\n--- SETUP --- admin={adm['color']} john={joh['color']} sarah={sar['color']}")

    # find john's and sarah's leads
    # ensure each owner has at least one lead (self-contained test)
    jl = c.get('/api/leads/', headers=J).get_json()
    sl = c.get('/api/leads/', headers=S).get_json()
    if not jl:
        c.post('/api/leads/', headers=J, json={'full_name': 'John Seed Lead', 'phone': '01711110001'})
        jl = c.get('/api/leads/', headers=J).get_json()
    if not sl:
        c.post('/api/leads/', headers=S, json={'full_name': 'Sarah Seed Lead', 'phone': '01711110002'})
        sl = c.get('/api/leads/', headers=S).get_json()
    chk('John has leads', len(jl) > 0, f'{len(jl)}')
    chk('Sarah has leads', len(sl) > 0, f'{len(sl)}')
    john_lead = jl[0]['id']
    sarah_lead = sl[0]['id']

    print('\n--- 1. CREATE EVENT FROM A LEAD ---')
    r = c.post('/api/events/', headers=A, json={
        'title': 'Site visit — Bashundhara plot',
        'start_datetime': '2026-11-10T10:00:00',
        'lead_id': john_lead,
        'description': 'Client wants to see block C',
    })
    chk('create event with lead_id', r.status_code == 201, f'HTTP {r.status_code}')
    ev = r.get_json()
    chk('event response has lead_id', ev.get('lead_id') == john_lead, f"lead_id={ev.get('lead_id')}")
    chk('event carries lead name', bool(ev.get('lead_name')), str(ev.get('lead_name')))
    chk("event colour = John's colour", ev.get('color') == joh['color'], f"{ev.get('color')} vs {joh['color']}")
    chk("event owner = John", ev.get('owner_name') == 'John Rahman', str(ev.get('owner_name')))
    event_id = ev['id']

    print('\n--- 2. LEAD-SCOPED ENDPOINTS ---')
    r = c.post(f'/api/events/lead/{sarah_lead}', headers=A, json={
        'title': 'Sarah lead call', 'start_datetime': '2026-11-11T14:00:00'})
    chk('POST /api/events/lead/<id>', r.status_code == 201, f'HTTP {r.status_code}')
    sarah_event = r.get_json()
    chk("Sarah's event uses Sarah's colour", sarah_event.get('color') == sar['color'], str(sarah_event.get('color')))

    r = c.get(f'/api/events/lead/{john_lead}', headers=A)
    lst = r.get_json()
    chk('GET /api/events/lead/<id>', r.status_code == 200 and any(e['id'] == event_id for e in lst),
        f'{len(lst)} event(s)')

    print('\n--- 3. RBAC — VISIBILITY ---')
    a_all = c.get('/api/events/', headers=A).get_json()
    j_all = c.get('/api/events/', headers=J).get_json()
    s_all = c.get('/api/events/', headers=S).get_json()

    def ev_ids(x): return {e['id'] for e in x if isinstance(e['id'], int)}
    chk('Admin sees both events', ev_ids(a_all) >= {event_id, sarah_event['id']},
        f'admin={len(ev_ids(a_all))}')
    chk("John sees his lead's event", event_id in ev_ids(j_all), f'john={len(ev_ids(j_all))}')
    chk("John CANNOT see Sarah's lead event", sarah_event['id'] not in ev_ids(j_all))
    chk("Sarah sees her lead's event", sarah_event['id'] in ev_ids(s_all), f'sarah={len(ev_ids(s_all))}')
    chk("Sarah CANNOT see John's lead event", event_id not in ev_ids(s_all))

    print('\n--- 4. RBAC — DETAIL + MUTATION ---')
    r = c.get(f'/api/events/{event_id}', headers=S)
    chk("Sarah blocked from John's event detail", r.status_code == 403, f'HTTP {r.status_code}')
    r = c.get(f'/api/events/{event_id}', headers=J)
    chk('John can read his event detail', r.status_code == 200)
    r = c.put(f'/api/events/{sarah_event["id"]}', headers=J, json={'title': 'hijacked'})
    chk("John blocked from editing Sarah's event", r.status_code == 403, f'HTTP {r.status_code}')
    r = c.delete(f'/api/events/{event_id}', headers=S)
    chk("Sarah blocked from deleting John's event", r.status_code == 403, f'HTTP {r.status_code}')

    print("\n--- 5. LEAD OWNER ADDS EVENT TO OWN LEAD ---")
    r = c.post('/api/events/', headers=J, json={
        'title': "John's own meeting", 'start_datetime': '2026-11-12T09:00:00', 'lead_id': john_lead})
    chk('lead owner can add event to own lead', r.status_code == 201, f'HTTP {r.status_code}')
    own_ev = r.get_json()
    r = c.post('/api/events/', headers=J, json={
        'title': 'cross-tenant', 'start_datetime': '2026-11-12T10:00:00', 'lead_id': sarah_lead})
    chk("lead owner blocked from other owner's lead", r.status_code == 403, f'HTTP {r.status_code}')

    print('\n--- 6. GENERAL (NON-LEAD) EVENT STILL WORKS ---')
    r = c.post('/api/events/', headers=J, json={'title': 'Team standup', 'start_datetime': '2026-11-13T09:00:00'})
    chk('general event created', r.status_code == 201, f'HTTP {r.status_code}')
    gen = r.get_json()
    chk('general event has no lead', gen.get('lead_id') is None)
    chk("general event uses John's colour", gen.get('color') == joh['color'], str(gen.get('color')))
    j2 = c.get('/api/events/', headers=J).get_json()
    chk('John sees his general event', gen['id'] in ev_ids(j2))
    s2 = c.get('/api/events/', headers=S).get_json()
    chk("Sarah does NOT see John's general event", gen['id'] not in ev_ids(s2))

    print('\n--- 7. LEAD COLOUR IN LEAD LIST ---')
    leads = c.get('/api/leads/', headers=A).get_json()
    colors = {l.get('assigned_to_name'): l.get('assigned_to_color') for l in leads if l.get('assigned_to_name')}
    chk("leads carry owner colour", bool(colors) and all(colors.values()), str(colors))

    print('\n--- 8. FACEBOOK CONNECT ---')
    r = c.get('/api/webhooks/facebook/status', headers=A)
    st = r.get_json()
    chk('status endpoint', r.status_code == 200 and st.get('connected') is False, f"connected={st.get('connected')}")

    r = c.get('/api/webhooks/facebook/oauth/start', headers=A)
    chk('oauth/start demands credentials first', r.status_code == 400, f'HTTP {r.status_code}')

    r = c.post('/api/webhooks/facebook/demo-connect', headers=A)
    d = r.get_json()
    chk('demo-connect works', r.status_code == 200 and d.get('success') is True)
    chk('demo returns forms', len(d.get('forms', [])) == 2, f"{len(d.get('forms', []))} forms")
    form = d['forms'][0]
    chk('form has questions', len(form['questions']) == 10, f"{len(form['questions'])} questions")

    r = c.get('/api/webhooks/facebook/status', headers=A)
    st = r.get_json()
    chk('status now connected', st.get('connected') is True, f"mode={st.get('mode')}")
    chk('status reports demo mode', st.get('mode') == 'demo')

    r = c.get('/api/webhooks/facebook/forms', headers=A)
    chk('forms endpoint', len(r.get_json().get('forms', [])) == 2)

    print('\n--- 9. IMPORT FACEBOOK QUESTIONS INTO CRM ---')
    before = c.get('/api/settings/questionnaire', headers=A).get_json()
    before_n = len(before) if isinstance(before, list) else len(before.get('questions', []))
    r = c.post(f"/api/webhooks/facebook/import-form/{form['id']}", headers=A)
    imp = r.get_json()
    chk('import-form succeeds', r.status_code == 200 and imp.get('success'), str(imp.get('message'))[:60])
    chk('native fields skipped (name/phone/email)', len(imp.get('skipped', [])) == 3, str(imp.get('skipped')))
    chk('questions written (created or updated)',
        len(imp.get('created', [])) + len(imp.get('updated', [])) > 0,
        f"{len(imp.get('created', []))} created / {len(imp.get('updated', []))} updated")

    after = c.get('/api/settings/questionnaire', headers=A).get_json()
    after_n = len(after) if isinstance(after, list) else len(after.get('questions', []))
    chk('CRM questionnaire has the form questions', after_n >= before_n, f'{before_n} -> {after_n}')

    # re-import should update, not duplicate
    r = c.post(f"/api/webhooks/facebook/import-form/{form['id']}", headers=A)
    imp2 = r.get_json()
    after2 = c.get('/api/settings/questionnaire', headers=A).get_json()
    after2_n = len(after2) if isinstance(after2, list) else len(after2.get('questions', []))
    chk('re-import is idempotent (no duplicates)', after2_n == after_n, f'{after_n} -> {after2_n}')

    print('\n--- 10. LEAD-OWNER CANNOT TOUCH FACEBOOK SETTINGS ---')
    r = c.post('/api/webhooks/facebook/demo-connect', headers=J)
    chk('lead owner blocked from demo-connect', r.status_code == 403, f'HTTP {r.status_code}')
    r = c.post('/api/webhooks/facebook/disconnect', headers=J)
    chk('lead owner blocked from disconnect', r.status_code == 403, f'HTTP {r.status_code}')

    print('\n--- 11. CLEANUP ---')
    r = c.post('/api/webhooks/facebook/disconnect', headers=A)
    chk('admin can disconnect', r.status_code == 200 and r.get_json().get('success'))
    st = c.get('/api/webhooks/facebook/status', headers=A).get_json()
    chk('status back to disconnected', st.get('connected') is False)

print('\n' + '='*70)
print(f'PASSED: {P}   FAILED: {F}')
print('='*70)
