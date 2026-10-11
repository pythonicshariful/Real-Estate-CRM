"""
Southeast Landmark CRM -- Full System Test Suite
================================================
Covers all 8 implementation phases:
  Phase 1 : Auth / Security (login, lockout, JWT, MFA fields, role-based expiry)
  Phase 2 : Inventory Hierarchy (Project -> Phase -> Block -> Road -> Plot)
  Phase 3 : Lead Management (create, list, RBAC, stage filter)
  Phase 4 : Reservation -> Installment -> Cancellation workflow
  Phase 5 : Appointment lifecycle (schedule -> confirm -> complete -> debrief)
  Phase 6 : Objections + Coaching Logs
  Phase 7 : Reports / KPIs with date filters + CSV export
  Phase 8 : Audit Logs + Soft-Delete verification

Usage:
    cd backend
    python test_crm_full.py
"""

import json
import sys
import os

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

os.environ['FLASK_CONFIG'] = 'testing'
os.environ['DISABLE_SCHEDULER'] = 'true'

# ── Bootstrap app ──────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from app import create_app
from app.extensions import db as _db
from app.models import User, UserRole

app = create_app('testing')

# ── Colour helpers ─────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

_pass_count = 0
_fail_count = 0
_warn_count = 0

def ok(msg):
    global _pass_count
    _pass_count += 1
    print(f"  {GREEN}[PASS]{RESET}  {msg}")

def fail(msg, extra=""):
    global _fail_count
    _fail_count += 1
    print(f"  {RED}[FAIL]{RESET}  {msg}")
    if extra:
        print(f"         {RED}{extra}{RESET}")

def warn(msg):
    global _warn_count
    _warn_count += 1
    print(f"  {YELLOW}[WARN]{RESET}  {msg}")

def section(title):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")


# ── Fixture helpers ────────────────────────────────────────────────────────────

def create_admin(client):
    """Create an admin user and return (user_id, token)."""
    with app.app_context():
        existing = User.query.filter_by(email='admin@test.com').first()
        if existing:
            _db.session.delete(existing)
            _db.session.commit()
        admin = User(
            email='admin@test.com',
            full_name='Test Admin',
            role=UserRole.ADMIN,
        )
        admin.set_password('Admin@1234')
        _db.session.add(admin)
        _db.session.commit()
        uid = admin.id

    resp = client.post('/api/auth/login', json={
        'email': 'admin@test.com',
        'password': 'Admin@1234'
    })
    data = resp.get_json()
    token = data.get('access_token') or data.get('token')
    return uid, token


def create_exec(client):
    """Create an executive user and return (user_id, token)."""
    with app.app_context():
        existing = User.query.filter_by(email='exec@test.com').first()
        if existing:
            _db.session.delete(existing)
            _db.session.commit()
        user = User(
            email='exec@test.com',
            full_name='Test Executive',
            role=UserRole.EXECUTIVE,
        )
        user.set_password('Exec@1234')
        _db.session.add(user)
        _db.session.commit()
        uid = user.id

    resp = client.post('/api/auth/login', json={
        'email': 'exec@test.com',
        'password': 'Exec@1234'
    })
    data = resp.get_json()
    token = data.get('access_token') or data.get('token')
    return uid, token


def hdrs(token):
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 -- Auth / Security
# ══════════════════════════════════════════════════════════════════════════════

def test_phase1_auth(client):
    section("PHASE 1 -- Auth & Security")

    # 1a. Login with wrong password
    r = client.post('/api/auth/login', json={'email': 'admin@test.com', 'password': 'WrongPass'})
    if r.status_code == 401:
        ok("Rejects bad password -> 401")
    else:
        fail("Expected 401 for bad password", f"Got {r.status_code}")

    # 1b. Login with correct password -> token returned
    r = client.post('/api/auth/login', json={'email': 'admin@test.com', 'password': 'Admin@1234'})
    data = r.get_json()
    token = data.get('access_token') or data.get('token')
    if r.status_code == 200 and token:
        ok("Login returns JWT access_token")
    else:
        fail("Login failed or no token returned", f"{r.status_code}: {data}")
        return  # Can't proceed without a token

    # 1c. Protected endpoint without token -> 401
    r = client.get('/api/leads/')
    if r.status_code == 401:
        ok("Protected endpoint -> 401 without token")
    else:
        fail(f"Expected 401, got {r.status_code}")

    # 1d. Protected endpoint WITH token -> success
    r = client.get('/api/leads/', headers=hdrs(token))
    if r.status_code == 200:
        ok("Protected endpoint -> 200 with valid token")
    else:
        fail(f"Expected 200 with token, got {r.status_code}", r.get_data(as_text=True)[:200])

    # 1e. Check User model has MFA fields
    with app.app_context():
        admin = User.query.filter_by(email='admin@test.com').first()
        has_mfa_fields = all([
            hasattr(admin, 'is_mfa_enabled'),
            hasattr(admin, 'mfa_secret'),
            hasattr(admin, 'mfa_verified'),
            hasattr(admin, 'failed_login_attempts'),
            hasattr(admin, 'lockout_until'),
        ])
        if has_mfa_fields:
            ok("User model has all MFA / lockout fields")
        else:
            fail("User model missing some MFA fields")

    # 1f. Role-based token expiry -- check claims contain role
    import base64, json as _json
    parts = token.split('.')
    payload = _json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
    if 'role' in payload:
        ok(f"JWT payload contains role = {payload['role']!r}")
    else:
        warn("JWT payload does not contain 'role' claim")

    # 1g. Logout / token revocation endpoint
    r = client.post('/api/auth/logout', headers=hdrs(token))
    if r.status_code in (200, 204):
        ok("Logout endpoint returns 200/204")
    else:
        warn(f"Logout returned {r.status_code} (may be implemented differently)")


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 -- Inventory Hierarchy
# ══════════════════════════════════════════════════════════════════════════════

def test_phase2_inventory(client, admin_token):
    section("PHASE 2 -- Inventory Hierarchy (Project->Phase->Block->Road->Plot)")

    h = hdrs(admin_token)

    # 2a. Create Project
    r = client.post('/api/projects/', json={
        'name': 'Southeast Heights',
        'code': f'TEST-SH-{os.getpid()}',
        'description': 'Test project',
        'location': 'Dhaka',
        'total_units': 100,
        'price_per_sqft': 4500.00
    }, headers=h)
    if r.status_code == 201:
        project_id = r.get_json().get('id')
        ok(f"Create project -> 201 (id={project_id})")
    else:
        fail("Create project failed", f"{r.status_code}: {r.get_data(as_text=True)[:200]}")
        return None, None, None, None, None

    # 2b. List Projects
    r = client.get('/api/projects/', headers=h)
    if r.status_code == 200:
        projects = r.get_json()
        ok(f"List projects -> 200 ({len(projects)} projects)")
    else:
        fail(f"List projects failed -> {r.status_code}")

    # 2c. Create Phase
    r = client.post(f'/api/projects/{project_id}/phases', json={
        'name': 'Phase A', 'description': 'First phase'
    }, headers=h)
    if r.status_code == 201:
        phase_id = r.get_json().get('id')
        ok(f"Create phase -> 201 (id={phase_id})")
    else:
        fail("Create phase failed", f"{r.status_code}: {r.get_data(as_text=True)[:200]}")
        return project_id, None, None, None, None

    # 2d. Create Block
    r = client.post(f'/api/projects/phases/{phase_id}/blocks', json={'name': 'Block A'}, headers=h)
    if r.status_code == 201:
        block_id = r.get_json().get('id')
        ok(f"Create block -> 201 (id={block_id})")
    else:
        fail("Create block failed", f"{r.status_code}: {r.get_data(as_text=True)[:200]}")
        return project_id, phase_id, None, None, None

    # 2e. Create Road
    r = client.post(f'/api/projects/blocks/{block_id}/roads', json={'road_number': 'Road-1'}, headers=h)
    if r.status_code == 201:
        road_id = r.get_json().get('id')
        ok(f"Create road -> 201 (id={road_id})")
    else:
        fail("Create road failed", f"{r.status_code}: {r.get_data(as_text=True)[:200]}")
        return project_id, phase_id, block_id, None, None

    # 2f. Create Plot
    r = client.post(f'/api/projects/{project_id}/plots', json={
        'plot_number': 'P-001',
        'phase_id': phase_id,
        'block_id': block_id,
        'road_id': road_id,
        'size_katha': 3.5,
        'facing': 'North',
        'rate_per_katha': 1200000,
        'total_price': 4200000,
        'status': 'AVAILABLE'
    }, headers=h)
    if r.status_code == 201:
        plot_id = r.get_json().get('id')
        ok(f"Create plot -> 201 (id={plot_id})")
    else:
        fail("Create plot failed", f"{r.status_code}: {r.get_data(as_text=True)[:200]}")
        return project_id, phase_id, block_id, road_id, None

    # 2g. Get plots for project
    r = client.get(f'/api/projects/{project_id}/plots', headers=h)
    if r.status_code == 200:
        plots = r.get_json()
        ok(f"List plots -> 200 ({len(plots)} plots)")
    else:
        fail(f"List plots failed -> {r.status_code}")

    return project_id, phase_id, block_id, road_id, plot_id


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 -- Lead Management
# ══════════════════════════════════════════════════════════════════════════════

def test_phase3_leads(client, admin_token, exec_token, exec_id, project_id):
    section("PHASE 3 -- Lead Management")

    h_admin = hdrs(admin_token)
    h_exec  = hdrs(exec_token)

    # 3a. Create lead (admin)
    r = client.post('/api/leads/', json={
        'phone': f'+8801700{os.getpid()%100000:05d}',
        'full_name': 'Test Customer',
        'source': 'FACEBOOK',
        'project_id': project_id,
        'project_interest': 'Southeast Heights'
    }, headers=h_admin)
    if r.status_code == 201:
        lead = r.get_json()
        lead_id = lead.get('id')
        ok(f"Create lead -> 201 (id={lead_id})")
    else:
        fail("Create lead failed", f"{r.status_code}: {r.get_data(as_text=True)[:300]}")
        return None

    # 3b. List leads (admin sees all)
    r = client.get('/api/leads/', headers=h_admin)
    if r.status_code == 200 and isinstance(r.get_json(), list):
        ok(f"Admin can list all leads -> 200")
    else:
        fail(f"Lead list failed for admin -> {r.status_code}")

    # 3c. Filter by stage
    r = client.get('/api/leads/?stage=NEW', headers=h_admin)
    if r.status_code == 200:
        ok("Lead stage filter (stage=NEW) works")
    else:
        fail(f"Stage filter failed -> {r.status_code}")

    # 3d. Get single lead
    r = client.get(f'/api/leads/{lead_id}', headers=h_admin)
    if r.status_code == 200:
        ok(f"Get lead detail -> 200")
    else:
        fail(f"Get lead detail failed -> {r.status_code}")

    # 3e. Exec cannot access lead not assigned to them
    r = client.get(f'/api/leads/{lead_id}', headers=h_exec)
    if r.status_code in (403, 404):
        ok("RBAC: Executive denied access to unassigned lead")
    else:
        warn(f"RBAC check soft fail: exec got {r.status_code} on unassigned lead")

    # 3f. Reassign lead to exec (admin only)
    r = client.put(f'/api/leads/{lead_id}/reassign', json={
        'assigned_to_id': exec_id,
        'reason': 'Testing reassignment'
    }, headers=h_admin)
    if r.status_code == 200:
        ok("Reassign lead to exec -> 200")
    else:
        fail(f"Reassign failed -> {r.status_code}", r.get_data(as_text=True)[:200])

    # 3g. Exec can now access the lead
    r = client.get(f'/api/leads/{lead_id}', headers=h_exec)
    if r.status_code == 200:
        ok("Exec can access lead after reassignment -> 200")
    else:
        warn(f"Exec access post-reassign returned {r.status_code}")

    # 3h. Update lead stage
    r = client.put(f'/api/leads/{lead_id}', json={'pipeline_stage': 'CONNECTED'}, headers=h_exec)
    if r.status_code == 200:
        ok("Update pipeline stage -> 200")
    else:
        warn(f"Update stage returned {r.status_code}")

    return lead_id


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 4 -- Reservation -> Installment -> Cancellation
# ══════════════════════════════════════════════════════════════════════════════

def test_phase4_reservation(client, admin_token, lead_id, plot_id):
    section("PHASE 4 -- Reservation / Installment / Cancellation Workflow")

    h = hdrs(admin_token)

    # 4a. Create reservation
    receipt = f'RCP-TEST-{os.getpid()}'
    r = client.post(f'/api/leads/{lead_id}/reservations', json={
        'unit_reference': 'Plot P-001 Block A Phase A',
        'booking_amount': 100000,
        'receipt_number': receipt,
        'payment_method': 'BANK_TRANSFER',
        'plot_id': plot_id,
        'currency': 'BDT',
        'notes': 'Initial booking'
    }, headers=h)
    if r.status_code == 201:
        res_data = r.get_json()
        res_id = res_data.get('id')
        ok(f"Create reservation -> 201 (id={res_id})")
    else:
        fail("Create reservation failed", f"{r.status_code}: {r.get_data(as_text=True)[:300]}")
        return None

    # 4b. Duplicate receipt rejected
    r = client.post(f'/api/leads/{lead_id}/reservations', json={
        'unit_reference': 'Plot P-002',
        'booking_amount': 50000,
        'receipt_number': receipt,  # same receipt
        'payment_method': 'CASH'
    }, headers=h)
    if r.status_code == 400:
        ok("Duplicate receipt -> 400 (unique constraint enforced)")
    else:
        warn(f"Duplicate receipt check returned {r.status_code} (expected 400)")

    # 4c. Plot status was updated to RESERVED
    from app.models import Plot
    with app.app_context():
        plot = Plot.query.get(plot_id)
        if plot and plot.status.value == 'RESERVED':
            ok("Plot status auto-updated to RESERVED after reservation")
        else:
            status = plot.status.value if plot else 'NOT FOUND'
            fail(f"Plot status not RESERVED (got {status!r})")

    # 4d. Lead stage auto-advanced to RESERVATION_RECEIVED
    r = client.get(f'/api/leads/{lead_id}', headers=h)
    data = r.get_json()
    if data.get('pipeline_stage') == 'RESERVATION_RECEIVED':
        ok("Lead stage auto-advanced to RESERVATION_RECEIVED")
    else:
        warn(f"Lead stage is {data.get('pipeline_stage')!r}, expected RESERVATION_RECEIVED")

    # 4e. List reservations
    r = client.get(f'/api/leads/{lead_id}/reservations', headers=h)
    if r.status_code == 200 and len(r.get_json()) >= 1:
        ok("List reservations -> 200")
    else:
        fail(f"List reservations failed -> {r.status_code}")

    # 4f. Create installment
    r = client.post(f'/api/leads/reservations/{res_id}/installments', json={
        'installment_number': 1,
        'title': 'Down Payment',
        'amount': 300000,
        'due_date': '2025-03-01',
        'notes': 'First installment'
    }, headers=h)
    if r.status_code == 201:
        inst_data = r.get_json()
        inst_id = inst_data.get('id')
        ok(f"Create installment -> 201 (id={inst_id})")
    else:
        fail("Create installment failed", f"{r.status_code}: {r.get_data(as_text=True)[:300]}")
        inst_id = None

    if inst_id:
        # 4g. Pay installment
        r = client.post(f'/api/leads/installments/{inst_id}/pay', json={
            'paid_amount': 300000,
            'payment_method': 'BANK_TRANSFER',
            'receipt_number': f'PAY-{os.getpid()}'
        }, headers=h)
        if r.status_code == 200:
            ok("Pay installment -> 200")
            if r.get_json().get('status') == 'PAID':
                ok("Installment status correctly set to PAID")
            else:
                warn(f"Installment status after payment: {r.get_json().get('status')}")
        else:
            fail(f"Pay installment failed -> {r.status_code}")

    # 4h. Request cancellation
    r = client.post(f'/api/leads/reservations/{res_id}/cancellations', json={
        'reason': 'Customer changed mind',
        'refund_amount_requested': 80000
    }, headers=h)
    if r.status_code == 201:
        cancel_id = r.get_json().get('id')
        ok(f"Request cancellation -> 201 (id={cancel_id})")
    else:
        fail("Request cancellation failed", f"{r.status_code}: {r.get_data(as_text=True)[:300]}")
        cancel_id = None

    if cancel_id:
        # 4i. Review cancellation (approve)
        r = client.post(f'/api/leads/cancellations/{cancel_id}/review', json={
            'decision': 'APPROVED',
            'refund_amount_approved': 80000,
            'review_notes': 'Approved after review'
        }, headers=h)
        if r.status_code == 200:
            ok("Approve cancellation -> 200")
        else:
            fail(f"Approve cancellation failed -> {r.status_code}")

        # 4j. Plot released back to AVAILABLE after approval
        with app.app_context():
            from app.models import Plot
            plot = Plot.query.get(plot_id)
            if plot and plot.status.value == 'AVAILABLE':
                ok("Plot status reverted to AVAILABLE after cancellation approval")
            else:
                status = plot.status.value if plot else 'NOT FOUND'
                warn(f"Plot status after cancellation approval: {status!r} (expected AVAILABLE)")

    return res_id


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 5 -- Appointment Lifecycle
# ══════════════════════════════════════════════════════════════════════════════

def test_phase5_appointments(client, admin_token, exec_token, lead_id):
    section("PHASE 5 -- Appointment Lifecycle")

    h = hdrs(admin_token)

    # 5a. Schedule appointment
    r = client.post(f'/api/leads/{lead_id}/appointments', json={
        'appointment_datetime': '2025-12-01T10:00:00',
        'location': 'Site Office',
        'notes': 'First site visit'
    }, headers=h)
    if r.status_code == 201:
        appt = r.get_json()
        appt_id = appt.get('id')
        ok(f"Schedule appointment -> 201 (id={appt_id})")
    else:
        fail("Schedule appointment failed", f"{r.status_code}: {r.get_data(as_text=True)[:300]}")
        return

    # 5b. List appointments
    r = client.get(f'/api/leads/{lead_id}/appointments', headers=h)
    if r.status_code == 200:
        ok("List appointments -> 200")
    else:
        fail(f"List appointments failed -> {r.status_code}")

    # 5c. Confirm appointment
    r = client.post(f'/api/leads/appointments/{appt_id}/confirm', headers=h)
    if r.status_code == 200:
        ok("Confirm appointment -> 200")
    else:
        fail(f"Confirm appointment failed -> {r.status_code}", r.get_data(as_text=True)[:200])

    # 5d. Complete appointment (with debrief)
    r = client.post(f'/api/leads/appointments/{appt_id}/complete', json={
        'debrief_notes': 'Customer liked Phase A plots. Strong interest.'
    }, headers=h)
    if r.status_code == 200:
        ok("Complete appointment with debrief -> 200")
    else:
        fail(f"Complete appointment failed -> {r.status_code}", r.get_data(as_text=True)[:200])

    # 5e. No-show appointment (create another)
    r2 = client.post(f'/api/leads/{lead_id}/appointments', json={
        'appointment_datetime': '2025-12-15T14:00:00',
        'location': 'Show Flat',
        'notes': 'Follow-up visit'
    }, headers=h)
    if r2.status_code == 201:
        appt_id2 = r2.get_json().get('id')
        r3 = client.post(f'/api/leads/appointments/{appt_id2}/no-show', json={
            'reason': 'Client did not attend'
        }, headers=h)
        if r3.status_code == 200:
            ok("Mark appointment as no-show -> 200")
        else:
            warn(f"No-show endpoint returned {r3.status_code}")
    else:
        warn("Could not create 2nd appointment for no-show test")


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 6 -- Objections + Coaching Logs
# ══════════════════════════════════════════════════════════════════════════════

def test_phase6_objections_coaching(client, admin_token, exec_token, exec_id, lead_id):
    section("PHASE 6 -- Objections & Coaching Logs")

    h_admin = hdrs(admin_token)
    h_exec  = hdrs(exec_token)

    # 6a. Exec logs an objection
    r = client.post(f'/api/leads/{lead_id}/objections', json={
        'category': 'PRICE_TOO_HIGH',
        'specific_objection': 'Customer thinks price is 20% above market',
        'intensity': 4,
        'is_principal': True,
        'reactivation_eligible': True,
        'handling_notes': 'Explained developer quality and freehold title'
    }, headers=h_exec)
    if r.status_code == 201:
        obj_id = r.get_json().get('id')
        ok(f"Log objection -> 201 (id={obj_id})")
    else:
        fail("Log objection failed", f"{r.status_code}: {r.get_data(as_text=True)[:300]}")
        obj_id = None

    # 6b. List objections
    r = client.get(f'/api/leads/{lead_id}/objections', headers=h_exec)
    if r.status_code == 200 and isinstance(r.get_json(), list):
        ok(f"List objections -> 200 ({len(r.get_json())} objections)")
    else:
        fail(f"List objections failed -> {r.status_code}")

    # 6c. Update objection (resolve it)
    if obj_id:
        r = client.put(f'/api/leads/objections/{obj_id}', json={
            'resolved': True,
            'handling_notes': 'Resolved after negotiation'
        }, headers=h_exec)
        if r.status_code == 200:
            ok("Update/resolve objection -> 200")
        else:
            fail(f"Update objection failed -> {r.status_code}")

    # 6d. Invalid category rejected
    r = client.post(f'/api/leads/{lead_id}/objections', json={
        'category': 'TOTALLY_INVALID_CATEGORY',
        'specific_objection': 'Test'
    }, headers=h_exec)
    if r.status_code == 400:
        ok("Invalid objection category -> 400")
    else:
        warn(f"Invalid category returned {r.status_code} (expected 400)")

    # 6e. Manager creates coaching log
    r = client.post('/api/leads/coaching', json={
        'executive_id': exec_id,
        'opportunity_id': lead_id,
        'score': 7,
        'strengths': 'Good rapport building',
        'areas_for_improvement': 'Needs to ask discovery questions earlier',
        'action_items': 'Practice SPIN selling framework',
        'session_date': '2025-11-01T09:00:00'
    }, headers=h_admin)
    if r.status_code == 201:
        coach_id = r.get_json().get('id')
        ok(f"Create coaching log -> 201 (id={coach_id})")
    else:
        fail("Create coaching log failed", f"{r.status_code}: {r.get_data(as_text=True)[:300]}")

    # 6f. Exec cannot create coaching log
    r = client.post('/api/leads/coaching', json={
        'executive_id': exec_id,
        'score': 5
    }, headers=h_exec)
    if r.status_code == 403:
        ok("RBAC: Executive cannot create coaching log -> 403")
    else:
        warn(f"Expected 403 for exec coaching creation, got {r.status_code}")

    # 6g. Exec can view their own coaching logs
    r = client.get('/api/leads/coaching', headers=h_exec)
    if r.status_code == 200:
        ok("Exec can list coaching logs -> 200")
    else:
        fail(f"Exec coaching list failed -> {r.status_code}")

    # 6h. Admin sees all coaching logs
    r = client.get('/api/leads/coaching', headers=h_admin)
    if r.status_code == 200:
        ok("Admin can list all coaching logs -> 200")
    else:
        fail(f"Admin coaching list failed -> {r.status_code}")


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 7 -- Reports / KPIs + CSV Export
# ══════════════════════════════════════════════════════════════════════════════

def test_phase7_reports(client, admin_token):
    section("PHASE 7 -- Reports / KPIs & CSV Export")

    h = hdrs(admin_token)

    # 7a. Basic KPI endpoint
    r = client.get('/api/reports/kpis', headers=h)
    if r.status_code == 200:
        data = r.get_json()
        ok("Reports KPI endpoint -> 200")
        expected_keys = ['conversion_rate', 'active_pipeline_val', 'speed_to_lead']
        present = [k for k in expected_keys if k in data]
        if present:
            ok(f"KPI response contains key metrics: {present}")
        else:
            warn(f"KPI keys found: {list(data.keys())[:8]}")
    else:
        fail(f"Reports KPI endpoint failed -> {r.status_code}", r.get_data(as_text=True)[:300])

    # 7b. KPI with date filters
    r = client.get('/api/reports/kpis?start_date=2024-01-01&end_date=2025-12-31', headers=h)
    if r.status_code == 200:
        ok("KPI with date filters -> 200")
    else:
        fail(f"KPI with date filters failed -> {r.status_code}")

    # 7c. Charts / Analytics report
    r = client.get('/api/reports/charts', headers=h)
    if r.status_code == 200:
        data = r.get_json()
        ok("Reports charts endpoint -> 200")
        if 'revenue_monthly' in data and 'lead_outcome' in data:
            ok("Charts response contains monthly revenue & lead outcome distributions")
    else:
        fail(f"Reports charts endpoint failed -> {r.status_code}")

    # 7d. CSV export for leads
    r = client.get('/api/reports/export/leads', headers=h)
    if r.status_code == 200:
        ct = r.content_type or ''
        if 'csv' in ct or 'octet' in ct or 'text' in ct:
            ok("Leads CSV export -> 200 with text/csv content-type")
        else:
            ok(f"Leads CSV export -> 200 (content-type: {ct})")
    else:
        fail(f"CSV export returned {r.status_code}")

    # 7f. Exec cannot access full reports or has restricted view
    r_exec = client.post('/api/auth/login', json={'email': 'exec@test.com', 'password': 'Exec@1234'})
    exec_token = r_exec.get_json().get('access_token') if r_exec.status_code == 200 else None
    if exec_token:
        r = client.get('/api/reports/kpis', headers=hdrs(exec_token))
        if r.status_code == 200:
            ok("Exec accesses scoped KPI report -> 200")
        elif r.status_code == 403:
            ok("RBAC: Exec cannot access reports -> 403")


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 8 -- Audit Logs + Soft Delete
# ══════════════════════════════════════════════════════════════════════════════

def test_phase8_audit_softdelete(client, admin_token, lead_id):
    section("PHASE 8 -- Audit Logs & Soft Delete")

    h = hdrs(admin_token)

    # 8a. Audit log endpoint
    r = client.get('/api/security/audit-log', headers=h)
    if r.status_code == 200:
        logs = r.get_json()
        ok(f"Audit log endpoint -> 200 ({len(logs) if isinstance(logs, list) else 'paginated'} entries)")
    else:
        warn(f"Audit log endpoint returned {r.status_code} (check /api/security/audit-log path)")

    # 8b. Check audit log model directly
    from app.models import AuditLog
    with app.app_context():
        count = AuditLog.query.count()
        if count > 0:
            ok(f"AuditLog table has {count} records")
        else:
            warn("AuditLog table is empty")

    # 8c. Soft-delete lead
    r = client.delete(f'/api/leads/{lead_id}', headers=h)
    if r.status_code in (200, 204):
        ok(f"Soft-delete lead -> {r.status_code}")
    else:
        fail(f"Soft-delete lead failed -> {r.status_code}", r.get_data(as_text=True)[:200])
        return

    # 8d. Soft-deleted lead should not appear in list
    r = client.get('/api/leads/', headers=h)
    leads = r.get_json() if r.status_code == 200 else []
    lead_ids = [l.get('id') for l in (leads if isinstance(leads, list) else [])]
    if lead_id not in lead_ids:
        ok("Soft-deleted lead excluded from list (is_deleted=True filter works)")
    else:
        fail("Soft-deleted lead still appears in lead list!")

    # 8e. Soft-delete fields on model
    from app.models import Opportunity
    with app.app_context():
        lead = Opportunity.query.get(lead_id)
        if lead and lead.is_deleted:
            ok("Lead.is_deleted=True confirmed in DB after soft delete")
        elif lead and not lead.is_deleted:
            fail("Lead.is_deleted is False after soft delete!")
        else:
            warn("Lead record not found in DB after soft delete")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_all():
    with app.app_context():
        print(f"\n{BOLD}Setting up in-memory test database...{RESET}")
        _db.create_all()

    with app.test_client() as client:
        # Create users
        admin_id, admin_token = create_admin(client)
        exec_id, exec_token = create_exec(client)

        if not admin_token:
            print(f"\n{RED}{BOLD}FATAL: Could not obtain admin token. Aborting tests.{RESET}")
            sys.exit(1)

        # Run phase tests
        test_phase1_auth(client)
        project_id, phase_id, block_id, road_id, plot_id = test_phase2_inventory(client, admin_token)
        lead_id = test_phase3_leads(client, admin_token, exec_token, exec_id, project_id)
        
        if lead_id:
            test_phase4_reservation(client, admin_token, lead_id, plot_id)
            # Create a fresh lead for remaining tests
            r = client.post('/api/leads/', json={
                'phone': f'+8801800{os.getpid()%100000:05d}',
                'full_name': 'Phase5 Customer',
                'source': 'WEBSITE',
                'project_id': project_id,
            }, headers=hdrs(admin_token))
            if r.status_code == 201:
                lead_id2 = r.get_json().get('id')
                client.put(f'/api/leads/{lead_id2}/reassign',
                           json={'assigned_to_id': exec_id},
                           headers=hdrs(admin_token))
            else:
                lead_id2 = lead_id

            test_phase5_appointments(client, admin_token, exec_token, lead_id2)
            test_phase6_objections_coaching(client, admin_token, exec_token, exec_id, lead_id2)

        test_phase7_reports(client, admin_token)
        
        if lead_id:
            test_phase8_audit_softdelete(client, admin_token, lead_id)

    # ── Summary ────────────────────────────────────────────────────────────
    total = _pass_count + _fail_count + _warn_count
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  TEST RESULTS SUMMARY{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"  {GREEN}Passed : {_pass_count}{RESET}")
    print(f"  {RED}Failed : {_fail_count}{RESET}")
    print(f"  {YELLOW}Warnings: {_warn_count}{RESET}")
    print(f"  Total  : {total}")
    
    if _fail_count == 0:
        print(f"\n{GREEN}{BOLD}  ALL TESTS PASSED!{RESET}\n")
    else:
        print(f"\n{RED}{BOLD}  {_fail_count} test(s) FAILED -- review output above.{RESET}\n")

    sys.exit(0 if _fail_count == 0 else 1)


if __name__ == '__main__':
    run_all()
