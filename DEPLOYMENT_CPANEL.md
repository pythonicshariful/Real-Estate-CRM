# Deploying to cPanel — Step-by-Step Guide

## What You Need
- A cPanel hosting account with **Python support**
- A MySQL database
- Your domain (`office.southeastlandmark.info`) pointed at your hosting

---

## Step 1: Create a MySQL Database in cPanel

1. Log in to cPanel
2. Find **MySQL Databases**
3. Create a new database — e.g., `southeas_crm`
4. Create a new database user — e.g., `southeas_crmuser` with a strong password
5. Add the user to the database with **All Privileges**
6. Note these values — you'll need them in your `.env`

---

## Step 2: Upload Your Files

1. In cPanel, open **File Manager**
2. Ensure all your files are inside `/home/southeas/repositories/Real-Estate-CRM/`
3. Check that the `.htaccess` and `passenger_wsgi.py` (the one I just rewrote for you) are in this root folder.
4. Manually create the uploads folder if it doesn't exist: `/home/southeas/repositories/Real-Estate-CRM/backend/uploads/`

---

## Step 3: Create Your .env File

1. In File Manager, navigate to `/home/southeas/repositories/Real-Estate-CRM/backend/`
2. Create or edit the `.env` file
3. Fill in your real database credentials:

```ini
FLASK_CONFIG=production
SECRET_KEY=generate-64-random-chars-here
JWT_SECRET_KEY=generate-another-64-random-chars
DATABASE_URL=mysql+pymysql://southeas_crmuser:YOUR_DB_PASSWORD@localhost/southeas_crm
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
META_VERIFY_TOKEN=some-random-string-you-choose
UPLOAD_FOLDER=/home/southeas/repositories/Real-Estate-CRM/backend/uploads
RECORDINGS_FOLDER=/home/southeas/repositories/Real-Estate-CRM/backend/uploads/recordings
```

---

## Step 4: Set Up Python App in cPanel

1. In cPanel, find **Setup Python App**
2. Click **Create Application** (or Edit your existing one)
3. Fill in:
   - **Python version**: `3.13`
   - **Application root**: `repositories/Real-Estate-CRM`
   - **Application URL**: `office.southeastlandmark.info`
   - **Application startup file**: `passenger_wsgi.py`
   - **Application Entry point**: `application`
4. Click **Create/Save**

---

## Step 5: Install Dependencies

1. Scroll down on the **Setup Python App** page to the **Configuration files** section.
2. If you see `backend/requirements.txt` or `requirements.txt`, click **Run Pip Install**.
3. If not, open the cPanel **Terminal** and run:
   ```bash
   source /home/southeas/virtualenv/repositories/Real-Estate-CRM/3.13/bin/activate
   cd /home/southeas/repositories/Real-Estate-CRM
   pip install -r backend/requirements.txt
   ```

---

## Step 6: Initialize the Database (If starting fresh)

If you haven't set up the database tables yet, do this in the cPanel Terminal:

```bash
source /home/southeas/virtualenv/repositories/Real-Estate-CRM/3.13/bin/activate
cd /home/southeas/repositories/Real-Estate-CRM/backend

# Create all database tables
flask db upgrade

# Create your first admin account
flask create-admin
# Enter your email, password, and name when prompted
```

---

## Step 7: Restart and Test

1. Go back to the **Setup Python App** page in cPanel.
2. Click the **Restart** button next to your application.
3. Open your browser and go to `https://office.southeastlandmark.info`

---

## Folder Permissions
Ensure these permissions in File Manager for security:
```text
backend/uploads/           → 755
backend/.env               → 600  (owner read-only)
```
