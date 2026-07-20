# Deploying to cPanel — Step-by-Step Guide

## What You Need
- A cPanel hosting account with **Python support** (most modern cPanel hosts have it)
- A MySQL database (cPanel creates these easily)
- Your domain or a subdomain pointed at your hosting

---

## Step 1: Create a MySQL Database in cPanel

1. Log in to cPanel
2. Find **MySQL Databases** (or MySQL Database Wizard)
3. Create a new database — e.g., `yourusername_crm`
4. Create a new database user — e.g., `yourusername_crmuser` with a strong password
5. Add the user to the database with **All Privileges**
6. Note these values — you'll need them in your `.env`

---

## Step 2: Upload Your Files

1. In cPanel, open **File Manager**
2. Navigate to your home directory (usually `/home/yourusername/`)
3. Create a folder called `crmforsouth`
4. Upload everything inside the `backend/` folder into `crmforsouth/`

Your directory should look like:
```
/home/yourusername/crmforsouth/
    app/
    migrations/
    uploads/          ← create this folder manually
    uploads/recordings/  ← create this subfolder too
    config.py
    passenger_wsgi.py
    requirements.txt
    .env              ← you will create this next
    ...
```

**Important:** Also upload the `frontend/` folder contents into:
```
/home/yourusername/crmforsouth/app/static/
```
So the HTML files are at `/home/yourusername/crmforsouth/app/static/index.html` etc.

---

## Step 3: Create Your .env File

1. In File Manager, navigate to `/home/yourusername/crmforsouth/`
2. Create a new file called `.env`
3. Copy the contents of `.env.example` into it
4. Fill in your real values:

```
FLASK_CONFIG=production
SECRET_KEY=generate-64-random-chars-here
JWT_SECRET_KEY=generate-another-64-random-chars
DATABASE_URL=mysql+pymysql://yourusername_crmuser:YOUR_DB_PASSWORD@localhost/yourusername_crm
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
META_VERIFY_TOKEN=some-random-string-you-choose
UPLOAD_FOLDER=/home/yourusername/crmforsouth/uploads
RECORDINGS_FOLDER=/home/yourusername/crmforsouth/uploads/recordings
```

> **Generate SECRET_KEY**: Go to https://djecrety.ir/ or run `python -c "import secrets; print(secrets.token_hex(32))"`

---

## Step 4: Set Up Python App in cPanel

1. In cPanel, find **Setup Python App** (or "Python App")
2. Click **Create Application**
3. Fill in:
   - **Python version**: Choose 3.11 or 3.12
   - **Application root**: `/home/yourusername/crmforsouth`
   - **Application URL**: Choose your domain or a subdomain like `crm.yourdomain.com`
   - **Application startup file**: `passenger_wsgi.py`
   - **Application Entry point**: `application`
4. Click **Create**

---

## Step 5: Install Dependencies

1. In the Python App panel, click **Enter to the virtual environment** (it shows a command like `source ...`)
2. Open cPanel **Terminal** and run that command to activate the virtual environment
3. Then install requirements:

```bash
cd /home/yourusername/crmforsouth
pip install -r requirements.txt
```

---

## Step 6: Initialize the Database

In the same Terminal:

```bash
cd /home/yourusername/crmforsouth
export FLASK_CONFIG=production
export DATABASE_URL="mysql+pymysql://yourusername_crmuser:PASSWORD@localhost/yourusername_crm"

# Create all database tables
flask db upgrade

# Create your first admin account
flask create-admin
# Enter your email, password, and name when prompted
```

---

## Step 7: Restart and Test

1. In cPanel Python App panel, click **Restart**
2. Open your browser and go to your domain/subdomain
3. You should see the CRM login page
4. Log in with the admin email/password you just created

---

## Troubleshooting

**500 Error on page load:**
- Check cPanel → Error Logs for the exact error
- Most common cause: wrong DATABASE_URL in .env
- Make sure the uploads/ folder exists and is writable

**ModuleNotFoundError:**
- Re-run `pip install -r requirements.txt` in the virtual environment

**Database connection refused:**
- On cPanel, the MySQL host is `localhost` (not an IP address)
- Double-check database name, username, and password

**Login page shows but can't log in:**
- Make sure you ran `flask create-admin`
- Check MAIL settings (required for some features)

---

## Folder Permissions

After uploading, set these permissions in File Manager:
```
uploads/           → 755
uploads/recordings/ → 755
.env               → 600  (owner read-only — important for security!)
```

---

## Keeping It Updated

When you make changes:
1. Upload the changed files
2. In cPanel Python App → Restart
3. If you changed models: run `flask db upgrade` in Terminal
