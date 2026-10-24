# Bug Fix Report — "Add Lead" button + Simulate Lead + Schedule Assignment

**Repo:** `pythonicshariful/Real-Estate-CRM` · **Date:** 2026-10-24
**Reported issues:** (1) Create Lead button does nothing, (2) Simulate Lead doesn't produce a lead, (3) leads should be assigned to Lead Owners according to schedule.

**Result: all three fixed.** 6 separate defects were found — 4 of them were blocking the features outright.

---

## Root causes

### 🔴 Bug 1 — `leads.js` had a fatal SyntaxError, so the whole file never ran

`app/static/assets/js/leads.js` declared `const importForm` **twice** in the same scope:

```js
line 1484:  const importForm = document.getElementById('import-lead-form');
line 2106:  const importForm = document.getElementById('import-leads-form');   // ← duplicate
```

A duplicate `const` in the same block is a **SyntaxError at parse time**. The browser therefore
discarded the entire 2,168-line file. Consequences:

- “Add Lead” button had no click handler → **nothing happened**
- `loadLeads()` never ran → the Leads table stayed completely **empty** (0 rows) even though the API
  was returning data
- Every other feature in that file (filters, drawer, import, bulk assign) was dead too

Verified in a real Chromium session before the fix:

```
PAGEERROR: Identifier 'importForm' has already been declared
rendered lead rows: 0
modal visible after click: false
```

**Fix:** renamed the second declaration to `csvImportForm` (+ comment explaining why).

---

### 🔴 Bug 2 — Lead creation returned 400 whenever the optional e-mail was left blank

The Add Lead form submits `""` for untouched optional inputs. The marshmallow schema declares:

```python
email = fields.Email(load_default=None)      # "" is NOT a valid email → ValidationError
```

So the single most common case in Bangladesh — a phone-only lead with no e-mail — failed with:

```json
{"code":400,"details":{"email":["Not a valid email address."]},"message":"Validation Error"}
```

The modal stayed open with a red toast and no lead was created.

**Fix (both ends):**
- `app/schemas.py` — added a `@pre_load` that turns blank optional strings into `None`
  (`full_name` / `phone` excluded so they still report as required).
- `app/static/assets/js/leads.js` — strips blank optional keys from the payload before POSTing.

---

### 🔴 Bug 3 — `assign_lead_owner_auto()` crashed with `NameError`

`app/tasks.py`:

```python
from app.models import User, UserRole, Opportunity        # PipelineStage missing!
...
terminal_stages = [PipelineStage.SOLD, ...]               # → NameError
```

**Auto-assignment had never worked.** The error was hidden because an earlier `return None` short-circuit
(see Bug 4) fired first, so the function never reached that line. Once any Lead Owner had a schedule
configured — or once the fallback was fixed — every assignment blew up:

```
ERROR in routes: Simulate lead error: NameError: name 'PipelineStage' is not defined
POST /api/settings/simulate-meta-lead → 500
```

**Fix:** added `PipelineStage` to the import.

---

### 🔴 Bug 4 — No fallback when nobody is inside their schedule window

`assign_lead_owner_auto()`'s own docstring promises:

> *“Otherwise, divide leads equally among all active Lead Owners (round-robin / lowest lead count).”*

The code did the opposite:

```python
if len(matching_scheduled_owners) > 0:
    candidate_pool = matching_scheduled_owners
else:
    logger.info("No active scheduled Lead Owners found. Leaving lead unassigned (Pending).")
    return None          # ← no fallback; lead left unassigned forever
```

Both seeded Lead Owners (John, Sarah) ship with **no schedule configured**, so *every* inbound lead was
silently left unassigned and never appeared in anyone's workspace.

**Fix:** fall back to `candidate_pool = active_owners` (lowest active-lead-count first = round-robin).

---

### 🟠 Bug 5 — Manually created leads were assigned to the Admin, not a Lead Owner

`create_lead()` hard-coded:

```python
opp = Opportunity(..., assigned_to_id=user_id, ...)
```

When an **Admin** creates a lead, `user_id` is the Admin — who is not a Lead Owner — so the lead never
showed up in any owner's workspace. **Fix:** if the creator is an Admin/Manager, route the lead through
`assign_lead_owner_auto()` (schedule-aware). A Lead Owner creating a lead still keeps it.

---

### 🟠 Bug 6 — Repeated “Simulate Lead” clicks merged into one lead instead of creating new ones

`process_meta_webhook()` deliberately merges a re-submitted Meta form into the existing contact's lead
(correct for real Facebook re-submissions). But the simulate tool defaults to a **fixed** phone
(`01799000111`, also prefilled in the Settings UI) and a fixed e-mail
(`testlead@simulate.com`) — so the 2nd, 3rd, 4th clicks all hit the same contact and were merged away.
The UI reported “✅ Simulated lead created” every time while the Leads page never grew.

**Fix:** `simulate_meta_lead` now rolls a fresh valid BD mobile number when the supplied number already
exists (`allow_duplicate: true` still forces a duplicate) and generates a unique e-mail when none is
given. The result box now shows the number actually used, plus a short note explaining why.

Verified — 5 clicks with the *same* prefilled number:

```
OK -> actual phone used: 01799000111
OK -> actual phone used: 01602247614
OK -> actual phone used: 01982206792
OK -> actual phone used: 01975847634
OK -> actual phone used: 01829297946
leads: 7 → 12
```

---

### 🟡 Bug 7 — `index.html` threw a three.js error on every load

The inline 3D background animation still queried `#auth-canvas`, but that element no longer exists in
the markup:

```
TypeError: Cannot read properties of null (reading 'width')
    at three.min.js  ← new THREE.WebGLRenderer({ canvas: null })
    at index.html:79
```

**Fix:** guarded the block with `if (document.getElementById('auth-canvas') && typeof THREE !== 'undefined')`.
Console is now clean on the login page.

---

## Verification

### Browser end-to-end (Playwright, real Chromium)

| Check | Result |
|---|---|
| Login via the UI form → redirects to `/admin-dashboard.html` | ✅ |
| JWT stored in localStorage | ✅ |
| Leads table renders rows with real data | ✅ |
| “Add Lead” modal opens on click | ✅ |
| Submit with **empty** optional e-mail succeeds | ✅ |
| New lead appears in table immediately | ✅ |
| New lead is assigned to a Lead Owner (not Admin, not Unassigned) | ✅ (Sarah Khan) |
| “Simulate Lead Now” clicked 3× → 3 leads created | ✅ |
| Simulated leads visible on the Leads page | ✅ |
| Lead Owner (John) sees his assigned leads in his own workspace | ✅ |
| JS console errors | **none** |

```
PASSED: 12   FAILED: 0
```

### Schedule-based assignment test

Set John → `00:00–23:59` (inside window), Sarah → `2020-01-01…2020-01-02` (outside):

```
5 simulated leads  →  all 5 assigned to John Rahman
```

Schedule window correctly overrides load-balancing, exactly as documented.

### API regression suite

```
TOTAL: 109   PASSED: 109   FAILED: 0   SUCCESS RATE: 100.0%
```

---

## Files changed

| File | Change |
|---|---|
| `backend/app/static/assets/js/leads.js` | renamed duplicate `importForm` const; strip blank fields before POST |
| `backend/app/schemas.py` | `@pre_load` blank-string → `None` |
| `backend/app/tasks.py` | import `PipelineStage`; fall back to all active owners |
| `backend/app/blueprints/leads/routes.py` | Admin-created leads auto-assign to a Lead Owner |
| `backend/app/blueprints/settings/routes.py` | simulate: unique phone/e-mail per click |
| `backend/app/static/settings.html` | result box shows the number actually used |
| `backend/app/static/index.html` | guard dead three.js background block |

```
7 files changed, 164 insertions(+), 55 deletions(-)
```

---

## Current state

The dev server is running on **port 5000** against `backend/crm_dev.db`:

- **12 leads**, all assigned — John Rahman 7, Sarah Khan 5, 0 unassigned
- Login: `admin@southeast.com` / `Admin@123`

> **Note:** the served frontend lives in `backend/app/static/`. The top-level `frontend/` folder is a
> stale duplicate — edits there have no effect.
