# Southeast Landmark CRM

A lead management and sales operations platform built for **Southeast Landmark Ltd.**, a real estate developer in Dhaka, Bangladesh. It captures leads from Meta (Facebook) Lead Ads and file imports, distributes them to sales executives under configurable rules, and tracks every follow-up — calls, events, appointments, dispositions — through to closing.

**Live:** https://southeastlandmark.pythonicshariful.tech

## Features

- **Lead pipeline** — Opportunities move through configurable pipeline stages with admin-defined temperature labels. Each lead profile brings together contact details, the full activity timeline, call logs with optional recording upload, notes, and every answer the customer gave on the lead form.
- **Meta Lead Ads integration** — A Facebook Page is connected from Settings with Facebook Login for Business; its lead forms sync automatically and new leads arrive in real time through webhooks, including all custom form questions and answers.
- **Excel / CSV import** — Upload with a preview and manual column-mapping step (including native Meta export files), duplicate detection, and automatic assignment.
- **Assignment engine** — Schedule-aware automatic assignment based on Lead Owners' duty windows (Asia/Dhaka), with lowest-count or round-robin fallback and per-owner capacity limits. Admins can also assign manually at any time.
- **Events and calendar** — Per-lead and standalone events with in-app reminders and notifications, on a colour-coded team calendar. Owner colours are managed centrally by the Admin.
- **Clients** — A contact directory with source, district, and growth analytics derived from lead data.
- **Reports and SLA** — Response-time (speed-to-lead) analytics restricted to management roles, configurable SLA thresholds, and automatic reassignment of stale leads.
- **Access control** — Role-based workspaces: the Admin sees all leads and team performance; Lead Owners see only their own. JWT authentication with optional TOTP multi-factor authentication.

## Tech stack

| Layer      | Technology                                             |
| ---------- | ------------------------------------------------------ |
| Backend    | Python 3, Flask 3, SQLAlchemy 2, Flask-JWT-Extended    |
| Database   | SQLite in production; any SQLAlchemy URL works         |
| Frontend   | Server-served HTML with vanilla JS, FullCalendar, Chart.js |
| Scheduling | APScheduler (in-process)                               |
| Serving    | Gunicorn behind nginx, managed by systemd              |

Datetimes are stored in UTC and presented in Asia/Dhaka throughout the UI.

## Project structure

```
backend/
  app/              Flask application — blueprints, models, background tasks
    static/         Web UI (HTML / CSS / JS)
  migrations/       Alembic migrations
  mega/             Vendored MEGA client for call-recording storage
  wsgi.py           Production WSGI entry point
  run.py            Development entry point
  cron.py           Scheduler entry point (used when DISABLE_SCHEDULER=True)
  test_*.py         Test suites
frontend/           Earlier standalone UI prototype (not served; kept for reference)
requirements.txt    Python dependencies
.env.example        Configuration template
```

## Getting started (development)

```bash
git clone https://github.com/pythonicshariful/Real-Estate-CRM.git
cd Real-Estate-CRM
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example backend/.env   # then fill in the values
cd backend && python run.py
```

With the development configuration the app creates a local SQLite database on first run.

## Configuration

Copy `.env.example` to `backend/.env` and set at least:

| Variable         | Purpose                                        |
| ---------------- | ---------------------------------------------- |
| `SECRET_KEY`     | Flask session secret                           |
| `JWT_SECRET_KEY` | Token signing secret                           |
| `DATABASE_URL`   | SQLAlchemy connection string                   |
| `MAIL_*`         | SMTP settings for outgoing mail                |
| `MEGA_*`         | MEGA account used for call-recording storage   |
| `DISABLE_SCHEDULER` | Set `True` when the scheduler runs via `cron.py` |

The Meta Lead Ads connection (app credentials and Page token) is managed in the app under **Settings → Meta** and stored in the database — it does not belong in `.env`.

## Testing

Each feature area has a `test_*.py` suite in `backend/`; run them with the project's virtual environment, for example:

```bash
cd backend
python test_event_reminders.py
python smoke_test.py   # end-to-end API smoke suite
```

## Deployment

Production runs on a Linux VPS: Gunicorn serves `backend/wsgi.py`, nginx terminates TLS and reverse-proxies to it, and a systemd unit keeps the service running. Updates are deployed by pulling the `main` branch and restarting the service.

## License

Proprietary software — © Southeast Landmark Ltd. All rights reserved.

Developed and maintained by [Shariful Islam](https://github.com/pythonicshariful).
