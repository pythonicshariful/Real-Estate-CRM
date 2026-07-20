# Real-Estate-CRM 🏢🚀
> **Enterprise-Grade Real Estate Lead Management & Sales Operations Platform**

A modern, full-featured Real Estate CRM system designed for high-performance property sales teams. Built with a robust **Flask (Python)** backend, **SQLAlchemy** ORM, and a sleek, modern glassmorphic web dashboard with **Chart.js** data visualizations and role-based workspace isolation.

---

## 🌟 Key Features

### 🛡️ 1. Two-Tiered Role-Based Access Control (RBAC)
- **Main Admin (`ADMIN`)**:
  - Centralized Command Center (`admin-dashboard.html`).
  - Total visibility across all Lead Owners, system metrics, and team performance.
  - Complete Lead Owner management (create accounts, assign color identities, set lead capacities, toggle active status, reset passwords).
  - Interactive charts (leads share by owner, daily new leads by owner, live activity stream across all owners).
- **Lead Owner (`LEAD_OWNER`)**:
  - Strictly isolated workspace (`dashboard.html`).
  - Access limited to personal leads, events, activities, call logs, and reports.
  - Theme-customized navigation bar with assigned color identity indicator.

### 🎨 2. Color-Coded Lead & Owner Tracking
- Main Admin assigns a unique hex color to each Lead Owner.
- Lead Owner colors persist throughout the entire application:
  - Lead cards display creator/owner color chips in Admin view.
  - Performance cards and charts in Admin Command Center use color themes.
  - Live activity feed items are tagged with owner color badges.

### ⚡ 3. Lead Management & SLA Engine
- **Speed-to-Lead SLA Monitoring**: Automatic tracking of 5-minute initial contact SLA with overdue alert banners and manager alerts.
- **Pipeline Stage Management**: Track opportunities through 20+ pipeline stages (New, Connected, Qualified, Appointment Scheduled, Sold, etc.).
- **Lead Temperature & Starring**: Mark leads as HOT 🔥, WARM ☀️, COLD ❄️, or FROZEN 🧊, and star high-priority leads.
- **Filtering & Export**: Modal-based filtering by stage, temperature, and starred status. One-click **Export to CSV/Excel**.

### 📅 4. Corporate Calendar & Event Management
- Full Calendar integration (`FullCalendar.js`) for corporate scheduling, appointments, and client site visits.
- Ownership-based event visibility.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, Flask, Flask-JWT-Extended, Flask-SQLAlchemy, Flask-CORS, PyJWT, Bcrypt, PyOTP (MFA support).
- **Database**: SQLite (Development) / PostgreSQL (Production).
- **Frontend**: HTML5, Vanilla JavaScript (ES Modules), TailwindCSS (CDN), Chart.js 4.4, FullCalendar 6.1.
- **Background Tasks**: APScheduler (SLA escalation timers).

---

## 📁 Repository Structure

```text
Real-Estate-CRM/
├── backend/
│   ├── app/
│   │   ├── blueprints/
│   │   │   ├── auth/          # Authentication & MFA routes
│   │   │   ├── dashboard/     # Role-aware statistics & analytics APIs
│   │   │   ├── events/        # Calendar event endpoints
│   │   │   ├── leads/         # Lead & opportunity endpoints with RBAC
│   │   │   ├── security/      # Audit logs & secure recording endpoints
│   │   │   ├── settings/      # System & SLA settings
│   │   │   └── team/          # Lead Owner account management (Admin only)
│   │   ├── static/            # Frontend Web App
│   │   │   ├── index.html           # Login screen
│   │   │   ├── admin-dashboard.html # Main Admin Command Center
│   │   │   ├── lead-owners.html     # Lead Owner management page
│   │   │   ├── dashboard.html       # Lead Owner personal dashboard
│   │   │   ├── leads.html           # Lead Engine dashboard
│   │   │   ├── events.html          # Corporate Calendar
│   │   │   └── assets/              # Styles, JS modules, icons
│   │   ├── models.py          # SQLAlchemy models (User, Opportunity, Contact, CallLog, etc.)
│   │   ├── tasks.py           # SLA background monitoring & notifications
│   │   └── commands.py        # CLI helpers
│   ├── run.py                 # Application entry point
│   ├── reset_db.py            # Database reset & seed script
│   └── requirements.txt       # Python dependencies
├── DEPLOYMENT_CPANEL.md       # Production deployment guide for cPanel
├── DEPLOYMENT_PYTHONANYWHERE.md # Production deployment guide for PythonAnywhere
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- `pip` package manager

### Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/pythonicshariful/Real-Estate-CRM.git
   cd Real-Estate-CRM
   ```

2. **Set Up Python Environment**:
   ```bash
   cd backend
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize & Seed Database**:
   ```bash
   python reset_db.py
   ```

5. **Run Development Server**:
   ```bash
   python run.py
   ```
   The application will be available at `http://127.0.0.1:5000/`.

---

## 🔑 Default Credentials

After running `python reset_db.py`, the system comes seeded with default accounts:

| Role | Email | Password | Assigned Color | Target View |
|---|---|---|---|---|
| **Main Admin** | `admin@southeast.com` | `Admin@123` | `#6366f1` (Indigo) | `/admin-dashboard.html` |
| **Lead Owner 1** | `john@southeast.com` | `John@123` | `#22c55e` (Green) | `/dashboard.html` |
| **Lead Owner 2** | `sarah@southeast.com` | `Sarah@123` | `#f59e0b` (Amber) | `/dashboard.html` |

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

---

**Developed with ❤️ by [pythonicshariful](https://github.com/pythonicshariful)**
