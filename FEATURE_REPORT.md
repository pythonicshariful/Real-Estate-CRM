# Lead Events · Owner Colours · Facebook Connect · UI Redesign

**Repo:** `pythonicshariful/Real-Estate-CRM` · **Date:** 2026-10-24
**Design system:** [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)

All 170 automated checks pass (44 events/Facebook API · 109 API smoke · 17 browser E2E).

---

## 1. Lead ↔ Event connection

Events now carry an optional `lead_id`. Everything that touches an event is lead-aware.

### Backend
`Event` model gained four columns (`auto-migrate` adds them on next start — no manual migration):

| Column | Purpose |
|---|---|
| `lead_id` | FK → `opportunities.id`, nullable (general events have none) |
| `owner_id` | User whose calendar colour the event uses |
| `resolved_owner()` | lead owner → owner → creator, in that order |

New / changed endpoints:

```
POST /api/events/                    → accepts lead_id (optional)
POST /api/events/lead/<lead_id>      → NEW: create straight from a lead
GET  /api/events/lead/<lead_id>      → NEW: all events of one lead
GET  /api/events/?lead_id=N          → NEW filter
```

`to_dict()` now also returns `lead_id`, `lead_name`, `lead_phone`, `lead_stage`, `owner_id`, `owner_name`, `created_by_name`.

### Frontend
- **Lead Details page** — a new **“Lead Events & Meetings”** card: inline create form (title / date-time / type / notes), a timeline of existing events (past ones dimmed), and per-event delete. Types: Site Visit, Call, Meeting, Follow-up.
- **Events page** — plus a **lead filter dropdown**, so you can view one lead's calendar in isolation.

---

## 2. Colour coding by Lead Owner

Every lead already knew its owner's colour (`calendar_color`); that colour is now used consistently:

- **Lead cards** — left border, avatar ring and avatar tint all take the owner's colour; the owner chip is now visible to **all roles** (previously admin-only).
- **Events** — a lead-linked event borrows the lead owner's colour; a general event uses its creator's. The Events page renders an **owner legend** and colour-tints each calendar chip.

> The seed accounts ship with: Main Admin `#6366f1`, John Rahman `#22c55e`, Sarah Khan `#f59e0b`. Admins can change them at Lead Owners → edit → colour.

---

## 3. Visibility rules (Admin sees all, users see their own)

| | Admin | Lead Owner |
|---|---|---|
| Events list | everything, colour-coded per owner | events they created **or** that belong to a lead assigned to them |
| Event detail / edit / delete | full access | 403 unless it's their event or their lead's event |
| Add event to a lead | any lead | only their own leads (403 otherwise) |
| Facebook settings | full access | 403 |

Verified explicitly: John cannot see, read, edit or delete Sarah's lead event — and vice-versa.

---

## 4. Facebook connection

Two modes, both live in **Settings → Meta Webhook & Guide**:

### Real OAuth (production)
1. Create an app at [developers.facebook.com](https://developers.facebook.com/apps/), add **Facebook Login** + **Webhooks**.
2. Paste **App ID / App Secret** into the new credentials box and copy the generated **Redirect URI** into *Valid OAuth Redirect URIs*.
3. Click **Connect with Facebook** → a popup runs the OAuth dialog with scopes
   `pages_show_list, pages_read_engagement, pages_manage_metadata, leads_retrieval, pages_manage_ads, business_management`.
4. The callback exchanges the code, picks your Page, stores a long-lived Page Access Token, and pulls the Page's **lead forms and their questions**.

```
GET  /api/webhooks/facebook/status
PUT  /api/webhooks/facebook/credentials
GET  /api/webhooks/facebook/oauth/start      → returns the dialog URL
GET  /api/webhooks/facebook/oauth/callback   → code → token → forms
POST /api/webhooks/facebook/sync-forms
POST /api/webhooks/facebook/disconnect
POST /api/webhooks/facebook/demo-connect     → no credentials needed
GET  /api/webhooks/facebook/forms
POST /api/webhooks/facebook/import-form/<form_id>
```

### Demo mode
Since real credentials can't exist in this sandbox, **“Try Demo Mode”** seeds a realistic connection (1 page + 2 lead forms with genuine question sets). The UI labels it **DEMO** everywhere so it can never be mistaken for a live connection. This exercises the exact same code path the real OAuth flow ends at.

### Same questions as Facebook ⇒ same fields in the CRM
`POST /api/webhooks/facebook/import-form/<id>` converts a Facebook form's questions into the CRM's lead questionnaire:

- native Facebook fields (`FULL_NAME`, `PHONE`, `EMAIL`) are **skipped** — they're already first-class lead fields
- every other question becomes a `LeadQuestionnaireQuestion` with its option list and a unique `question_key`
- re-importing is **idempotent**: existing questions are updated, never duplicated

Verified end-to-end: importing *Apartment Launch — Elite Society* produced `2 new, 2 updated, 3 skipped (native fields)` and the questionnaire grew 12 → 17. Those questions then appear on every lead (manual and Meta-sourced), because `process_meta_webhook` already maps `field_data` by key.

---

## 5. UI redesign

Built from the **ui-ux-pro-max** design-system generator (`search.py … --design-system`):

| | Before | After |
|---|---|---|
| **Style** | ad-hoc dark glass | Glassmorphism with a proper token layer |
| **Palette** | Indigo / violet (`#6366f1`) | **Trust Teal `#0F766E`** + professional blue `#0369A1` (light) / `#14B8A6` + `#38BDF8` (dark) |
| **Typography** | Inter only | **Cinzel** display · **Plus Jakarta Sans** UI · **Fira Code** for numbers/IDs |
| **Themes** | dark only | **Light + Dark**, toggle in every page header, persisted in `localStorage`, `prefers-color-scheme` aware |
| **Accessibility** | — | visible focus rings, `prefers-reduced-motion`, 44 px touch targets, ARIA labels on the toggle |

Delivered as two new files loaded by all 27 pages:

- `assets/css/theme.css` — full token system (light + dark), component classes, FullCalendar theming, and a **compatibility layer** that remaps the pages' hard-coded dark Tailwind utilities (`bg-[#0a0a14]`, `text-slate-300`, …) under the light theme, so 28 existing pages adapt without a rewrite.
- `assets/js/theme.js` — injects a segmented sun/moon toggle into each header, persists the choice, and supports **Shift + D** as a keyboard shortcut.

Also fixed along the way: the Events and Lead Details pages had page-level `<style>` blocks re-hardcoding dark hex values — those now use theme tokens. The calendar toolbar title is theme-aware (it was an invisible white-to-slate gradient). Dashboard chart titles were `#e2e8f0` on white — now tokenised.

---

## Files

**New (7)**
```
backend/app/blueprints/webhooks/facebook.py   OAuth + demo + form import
backend/app/static/assets/css/theme.css       design system (559 lines)
backend/app/static/assets/js/theme.js         theme controller
backend/test_events_facebook.py               44-check suite
BUGFIX_REPORT_ROUND2.md · TEST_REPORT.md      earlier reports
```

**Modified (28)**
```
backend/app/models.py                          Event.lead_id / owner_id / to_dict
backend/app/blueprints/events/routes.py        RBAC helpers, lead linkage, filters
backend/app/blueprints/webhooks/__init__.py    register facebook module
backend/app/static/events.html                 legend, lead filter, lead-aware chips
backend/app/static/lead-details.html           Lead Events card (create/list/delete)
backend/app/static/settings.html               Connect-with-Facebook panel
backend/app/static/assets/js/leads.js          owner-coloured cards
backend/app/static/*.html  (27 pages)          theme.css + theme.js
```

---

## Verify it

```bash
cd backend
../.venv/bin/python test_events_facebook.py   # 44 checks — events, RBAC, Facebook
../.venv/bin/python smoke_test.py             # 109 API checks
```

Browser: server is on **port 5000** (`admin@southeast.com` / `Admin@123`).

1. **Leads** → every card is colour-coded by owner · toggle light/dark top-right (or `Shift+D`)
2. Open any lead → scroll to **Lead Events & Meetings** → **Add Event** → it appears instantly and on the calendar
3. **Events** → owner legend, lead filter, colour-tinted events
4. **Settings → Meta** → **Try Demo Mode** → two lead forms appear → **Import questions to CRM**
5. Log in as `john@southeast.com` / `John@123` to confirm he only ever sees his own leads and events

---

## One caveat

Real Facebook OAuth needs **HTTPS + a public domain** — Facebook rejects `localhost`. Nothing can change that; it's why Demo Mode exists. Once you deploy to your cPanel/PythonAnywhere domain, add the App credentials there and the live flow will work as-is.
