# Deploying to PythonAnywhere — Step-by-Step Guide

## Why PythonAnywhere?
PythonAnywhere is beginner-friendly, has a free tier for testing, and is
specifically designed for Python web apps. It handles WSGI automatically.

**Free plan limitations:** 1 web app, no custom domain, limited storage.
**Paid plan ($5/month):** Custom domain, more storage, more CPU.

---

## Step 1: Create a PythonAnywhere Account

1. Go to https://www.pythonanywhere.com
2. Sign up for a free account (or paid for custom domain)
3. Note your username — your site will be at `yourusername.pythonanywhere.com`

---

## Step 2: Create a MySQL Database

1. In PythonAnywhere dashboard, click **Databases** tab
2. Set a MySQL password (remember this!)
3. Create a new database — it will be named `yourusername$crmdb`
4. Your connection string will be:
   ```
   mysql+pymysql://yourusername:YOUR_MYSQL_PASSWORD@yourusername.mysql.pythonanywhere-services.com/yourusername$crmdb
   ```

---

## Step 3: Upload Your Files

**Option A: Using the PythonAnywhere Files tab (simplest)**
1. Click **Files** tab in dashboard
2. Navigate to `/home/yourusername/`
3. Create directory `crmforsouth`
4. Upload all files from your `backend/` folder into `crmforsouth/`

**Option B: Using Git (recommended if you have GitHub)**
1. Open a **Bash Console** from the dashboard
2. Run:
   ```bash
   git clone https://github.com/yourusername/crmforsouth.git
   ```

**Upload frontend files:**
```bash
# In the Bash console:
cp -r /home/yourusername/crmforsouth/frontend/* /home/yourusername/crmforsouth/app/static/
```

---

## Step 4: Create Your .env File

In the Bash Console:
```bash
cd /home/yourusername/crmforsouth
cp .env.example .env
nano .env
```

Edit the values:
```
FLASK_CONFIG=production
SECRET_KEY=64-random-chars-here
JWT_SECRET_KEY=another-64-random-chars
DATABASE_URL=mysql+pymysql://yourusername:MYSQL_PASSWORD@yourusername.mysql.pythonanywhere-services.com/yourusername$crmdb
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
META_VERIFY_TOKEN=some-random-string
UPLOAD_FOLDER=/home/yourusername/crmforsouth/uploads
RECORDINGS_FOLDER=/home/yourusername/crmforsouth/uploads/recordings
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

---

## Step 5: Install Dependencies

In the Bash Console:
```bash
cd /home/yourusername/crmforsouth
pip3 install --user -r requirements.txt
```

This takes 2-3 minutes. You'll see packages installing.

---

## Step 6: Create Upload Folders

```bash
mkdir -p /home/yourusername/crmforsouth/uploads/recordings
chmod 755 /home/yourusername/crmforsouth/uploads
chmod 755 /home/yourusername/crmforsouth/uploads/recordings
```

---

## Step 7: Initialize the Database

```bash
cd /home/yourusername/crmforsouth
export FLASK_CONFIG=production

# Run migrations (creates all tables)
flask db upgrade

# Create your first admin account
flask create-admin
# Enter: Email, Password (twice), Full Name
```

---

## Step 8: Configure the Web App

1. In PythonAnywhere dashboard, click **Web** tab
2. Click **Add a new web app**
3. Choose **Manual configuration** (NOT Flask — we want manual)
4. Choose **Python 3.11**
5. Click Next until it's created

**Configure the WSGI file:**
1. In the Web tab, find **WSGI configuration file** and click the link
2. Delete all the existing content
3. Paste this:

```python
import sys
import os

project_dir = '/home/yourusername/crmforsouth'
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, '.env'))
os.environ.setdefault('FLASK_CONFIG', 'production')

from app import create_app
application = create_app('production')
```

4. Save the file

**Configure static files (to serve the frontend):**
In the Web tab, under **Static files**, add:
- URL: `/static/`
- Directory: `/home/yourusername/crmforsouth/app/static`

---

## Step 9: Reload and Test

1. In the Web tab, click the green **Reload** button
2. Visit `https://yourusername.pythonanywhere.com`
3. You should see the CRM login page

---

## Step 10: Custom Domain (Paid Plan Only)

1. In Web tab, click **Add a custom domain**
2. Enter your domain (e.g., `crm.yourcompany.com`)
3. In your domain registrar (GoDaddy, Namecheap, etc.), add a CNAME record:
   - Name: `crm`
   - Value: `yourusername.pythonanywhere.com`
4. HTTPS is automatically provided by PythonAnywhere ✅

---

## Scheduled Tasks (SLA Timers Note)

PythonAnywhere runs your Flask app as a **WSGI process**. The APScheduler
inside Flask will run SLA timers as background threads within that process.

**Important:** PythonAnywhere **restarts your web app** if it's idle for
a while (on free plan). This means:
- Any pending scheduled SLA timers stored only in memory will be lost on restart
- **Solution**: The app uses SQLAlchemy jobstore — jobs are stored in the
  database and survive restarts automatically ✅

For extra reliability, add a PythonAnywhere **Scheduled Task**:
1. In dashboard → **Tasks** tab
2. Add a task to run every hour:
   ```bash
   cd /home/yourusername/crmforsouth && flask check-sla
   ```
   This is a fallback sweep that catches any missed SLA escalations.

---

## Troubleshooting

**Error log location:**
Web tab → Log files → Error log

**Common issues:**

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError` | Run `pip3 install --user -r requirements.txt` again |
| `OperationalError: Can't connect to MySQL` | Check DATABASE_URL in .env — use `yourusername.mysql.pythonanywhere-services.com` as host |
| `404 on all pages` | Check WSGI file path — must match exactly |
| `500 on login` | Check MAIL settings in .env |
| SLA timers not firing | Add hourly scheduled task (see above) |

---

## Free vs Paid Comparison

| Feature | Free | Paid ($5/mo) |
|---------|------|-------------|
| Web app | 1 | 2+ |
| Custom domain | ❌ | ✅ |
| Storage | 512 MB | 5 GB+ |
| CPU (daily) | 100 sec | Unlimited |
| MySQL databases | 1 | Multiple |
| App always-on | ❌ (sleeps) | ✅ |

> For a production CRM, the **Hacker plan ($5/month)** is recommended
> for always-on service and custom domain.
