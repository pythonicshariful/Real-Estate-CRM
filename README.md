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

## 🔑 Default Credentials

After running `python reset_db.py`, the system comes seeded with default accounts:

| Role | Email | Password | Assigned Color | Target View |
|---|---|---|---|---|
| **Main Admin** | `admin@southeast.com` | `Admin@123` | `#6366f1` (Indigo) | `/admin-dashboard.html` |
| **Lead Owner 1** | `john@southeast.com` | `John@123` | `#22c55e` (Green) | `/dashboard.html` |
| **Lead Owner 2** | `sarah@southeast.com` | `Sarah@123` | `#f59e0b` (Amber) | `/dashboard.html` |

---

## 📖 User Manual & Operational Guide

### 1. Login & Authentication
1. Open your browser and navigate to `http://127.0.0.1:5000/` (or your deployed URL).
2. Enter your registered email address and password.
3. Upon authentication, the system automatically redirects you based on your role:
   - **Main Admin** → `admin-dashboard.html`
   - **Lead Owner** → `dashboard.html`

---

### 2. Main Admin Operational Manual

#### A. Accessing the Admin Command Center (`admin-dashboard.html`)
- **System KPIs**: At the top of the dashboard, review high-level metrics:
  - *Total Lead Owners*, *Total Leads*, *Overdue SLA Count*, and *Closed Won Count*.
- **Lead Owner Performance Cards**: Grid cards displaying real-time metrics for every sales executive:
  - Total Leads, New Leads Today, Overdue Leads, and Closed Won Deals.
  - Cards are styled with each owner's assigned brand color.
- **Interactive Analytics**:
  - *Leads Distribution by Owner* (Doughnut Chart).
  - *Today's New Leads by Owner* (Bar Chart).
  - *Lead Owner Filter*: Filter the entire command center view by selecting a specific Lead Owner from the top-right header dropdown.
- **Live Activity Feed**: Monitor real-time logs (calls, notes, stage changes) performed across all Lead Owners, tagged with owner color avatars.

#### B. Managing Lead Owners (`lead-owners.html`)
- Click **"Lead Owners"** in the sidebar (or click *"Manage Owners →"* on the Admin Dashboard).
- **Add New Lead Owner**:
  1. Click the **"+ Add Lead Owner"** button in the header.
  2. Fill in *Full Name*, *Email*, *Phone*, *Password*, and *Max Lead Capacity*.
  3. **Assign Color**: Use the color picker or click one of the preset color palette circles to assign a unique visual identity to the Lead Owner.
  4. Click **"Create Owner"**.
- **Edit Lead Owner**: Click **"Edit"** on any Lead Owner card to change their name, phone, color theme, or lead capacity.
- **Reset Password**: Click **"Reset Pwd"** to assign a new password to a team member.
- **Activate / Deactivate**: Click **"Deactivate"** to temporarily block access (or **"Activate"** to restore account access).

#### C. Viewing All Leads & Filtering by Owner (`leads.html`)
- As Main Admin, navigating to `/leads.html` lists **all leads across the entire organization**.
- Each lead card features an **Owner Badge** showing the assigned Lead Owner's name and color theme.
- **Filter by Owner**: Click a lead card's *"View Leads"* link from the Admin Dashboard to automatically filter the lead engine to a specific owner (e.g. `/leads.html?owner=2`).

---

### 3. Lead Owner Operational Manual

#### A. Working in Your Isolated Workspace (`dashboard.html`)
- As a Lead Owner, your workspace is **100% private**. You can only see data assigned to you.
- **Personal Navigation Bar**: The sidebar displays a visual color strip reminding you of your assigned color identity.
- **Personal Dashboard**: View your personal statistics (*My Leads Today*, *My SLA Status*, *My Upcoming Appointments*, *My Performance*).

#### B. Lead Engine Operations (`leads.html`)
- **Adding a New Lead**:
  1. Click **"+ Add Lead"** in the header.
  2. Enter the prospect's *Full Name*, *Phone Number*, *Email*, and optional *Project Interest*.
  3. Click **"Save Lead"**. The lead is automatically assigned to you.
- **Managing Lead Temperature & Priority**:
  - Click the temperature badge on a lead card to toggle between **HOT** 🔥, **WARM** ☀️, and **COLD** ❄️.
  - Click the **Star icon** (⭐) to pin high-priority leads to the top.
- **Logging Activity & Short Notes**:
  - Click **"Log Activity"** on a lead card to record phone calls, call outcomes (Connected, Voicemail, Busy), and next follow-up deadlines.
  - Open a lead profile to view call history, log notes, and upload call recordings.
- **Booking Appointments**:
  - Select **"Book Appt"** inside a lead drawer to schedule client site visits or project presentations.
- **Responding to Speed-to-Lead SLA Alerts**:
  - If a lead has not received first contact within 5 minutes, a red **SLA Alert Banner** appears at the top.
  - Immediately log a call or activity to resolve the SLA breach and clear the banner.
- **Filtering & Exporting**:
  - Click **"Filter"** to slice your leads by stage, temperature, or starred status.
  - Click **"Export"** to download your currently filtered leads as a CSV spreadsheet.

#### C. Personal Corporate Calendar (`events.html`)
- Access `/events.html` to view scheduled meetings, appointments, and client site visits.
- Click any date to add a new event or reminder.

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

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

---

**Developed with ❤️ by [pythonicshariful](https://github.com/pythonicshariful)**
