# Real-Estate-CRM — Local Run & Test Report

**Repo:** `pythonicshariful/Real-Estate-CRM` (branch `main`, commit `76d9abc`)
**Tested:** 2026-10-24
**Environment:** Python 3.13.16 · Flask 3 · SQLite (`backend/crm_dev.db`) · scheduler active (APScheduler)

---

## 1. Was it runnable out of the box?

**Yes, with zero code changes.** The `development` config automatically falls back to SQLite, so no MySQL
server, no MEGA account, no SMTP credentials were needed.

Steps that worked:

```bash
cd Real-Estate-CRM
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # clean, no conflicts
cd backend
cp .env.example .env        # FLASK_CONFIG=development, dummy secrets
../.venv/bin/python reset_db.py      # created 40+ tables, seeded settings/project/users
../.venv/bin/python run.py          # serves on 0.0.0.0:5000
```

`reset_db.py` seeded the documented accounts:

| Role | Email | Password |
|---|---|---|
| ADMIN | admin@southeast.com | Admin@123 |
| LEAD_OWNER | john@southeast.com | John@123 |
| LEAD_OWNER | sarah@southeast.com | Sarah@123 |

Sample project **Elite Society (ELITE-SOC)** was created too.

---

## 2. Test results

Wrote an end-to-end smoke suite (`backend/smoke_test.py`) that drives the real Flask test client through
login → CRUD → RBAC → delete → logout across every module.

```
TOTAL: 109   PASSED: 109   FAILED: 0   SUCCESS RATE: 100.0%
```

**179 routes registered** across 20 blueprints. Modules exercised:

`auth` · `dashboard` · `leads` · `contacts` · `projects` · `team` · `tasks` · `events` · `notes` ·
`messages` · `tickets` · `finance` · `expenses` · `reports` · `settings` (11 sub-endpoints) ·
`security` · `help` · `prospects` · `webhooks` · RBAC enforcement

### What was verified
- Login for ADMIN and LEAD_OWNER, wrong-password rejection (401), JWT `me`/`me/stats`
- Logout revokes the token — subsequent call correctly returns **401 “Token has been revoked”**
- Full lead lifecycle: create → detail → profile → update → temperature → star → note → call log →
  appointment → questionnaire → reassign → bulk assign → soft delete
- Duplicate-lead engine: second create with the same phone correctly returns **409** with the
  owning agent + pipeline stage
- Project hierarchy: project → phase → block → plot
- Task / event / note / message / ticket create-update-delete
- All 11 settings endpoints, audit log, Meta webhook verification handshake (`hub.challenge` echoed)
- **RBAC**: LEAD_OWNER blocked with 403 from `/api/team/lead-owners` and `/api/settings/general`
- Static page serving: `/`, `/index.html`, `/dashboard.html`, `/leads.html`, `/admin-dashboard.html`,
  `/assets/...` all return 200 — API base in the frontend is the relative path `/api`, so it works
  behind any proxy

---

## 3. Bugs found (both real, both fixed)

### Bug 1 — Creating a lead with a budget crashed with HTTP 500 🔴

`app/blueprints/leads/routes.py`, `create_lead()`

```python
raw_payload=validated_data,     # ← marshmallow loaded budget_min/budget_max as Decimal
```

`Inquiry.raw_payload` is a `db.JSON` column. Python `Decimal` is not JSON-serializable, so SQLAlchemy
raised `TypeError: Object of type Decimal is not JSON serializable` and every lead submission that
included `budget_min` / `budget_max` failed — **this includes the Meta/Facebook lead form path**, which
passes budgets. Leads without a budget worked fine, which is why it could go unnoticed.

Also noticed while fixing: `original_phone_raw`, `budget_min` and `budget_max` columns on `Inquiry`
existed but were never populated.

**Fix applied** — coerce Decimals to float for the JSON payload and populate the real columns:

```python
raw_payload = {k: (float(v) if isinstance(v, Decimal) else v) for k, v in validated_data.items()}
inquiry = Inquiry(
    ...
    original_phone_raw=phone,
    budget_min=validated_data.get('budget_min'),
    budget_max=validated_data.get('budget_max'),
    raw_payload=raw_payload,
    ...
)
```

### Bug 2 — Logging a call without a recording returned HTTP 500 🔴

`app/blueprints/leads/routes.py`, `log_call()`

The `return jsonify(resp_data), 201` sat **inside** the `if recording_file and recording_file.filename:`
block. Logging a call with no audio attached — the normal case — fell off the end of the function and
returned `None`, producing:

```
TypeError: The view function for 'leads.log_call' did not return a valid response.
```

**Fix applied** — added the fallback return after the block:

```python
return jsonify({"id": log.id, "msg": "Call logged", "recording_url": None}), 201
```

Both fixes are 18 added lines in one file (`git diff --stat`: 1 file changed, 18 insertions, 1 deletion).

---

## 4. Observations (not fixed — flagged for you)

| # | Severity | Observation |
|---|---|---|
| 1 | Medium | **`/api/settings/*` leaks secrets in plaintext.** `GET /api/settings/email-templates` returns `smtp_password`; `/api/settings/b2-storage` returns `b2_application_key`; `/api/settings/meta-webhook` returns `meta_app_secret` and the page access token. Any ADMIN token can read them. Prefer write-only fields + masked reads. |
| 2 | Medium | **Login rate-limit is 5/min but rate-limit state is stored in the main DB.** Under a burst the admin account gets a 429 before lockout logic even runs. Fine for prod, but it bit the test run — worth an env switch. |
| 3 | Medium | **`_auto_migrate_db()` runs `ALTER TABLE` on every app start**, at import time, in the same process that serves traffic. On a busy cPanel box a table lock during startup can hang requests. Alembic is already installed — consider using it. |
| 4 | Low | **Package drift.** `frontend/` is a stale copy of `backend/app/static/` (only the latter is served); `Makefile` still references `docker-compose` which no longer exists in the repo; `requirements.txt` exists at both root and `backend/` with the same content. |
| 5 | Low | **`GET /api/leads/import` is registered twice** (`POST /api/leads/import` appears twice in the URL map) — one shadows the other. |
| 6 | Low | **`temp_leads.html` is an empty file committed to the repo**, and `test.txt` / `refactor*.py` / `fix_admin*.py` are dev leftovers at repo root. |
| 7 | Info | `testing` config uses `sqlite:///:memory:` with `StaticPool` — workable, but the app factory still calls `_auto_migrate_db()`, so unit tests carry the startup ALTER-TABLE cost. |

---

## 5. How to reproduce

```bash
cd backend
../.venv/bin/python smoke_test.py     # 109 assertions, writes smoke_test_results.json
```

The dev server is currently running on **port 5000** with login `admin@southeast.com / Admin@123`.
