import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Ensure backend root is in Python path
BACKEND_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.tasks import check_sla_compliance, send_daily_summary

def run_jobs():
    """Manually run background jobs outside the web worker context."""
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
    
    app = create_app()
    with app.app_context():
        print(f"[{datetime.now()}] Running SLA compliance check...")
        check_sla_compliance()
        print(f"[{datetime.now()}] SLA compliance check completed.")
        
        # In a real environment, daily summary should be checked against a flag.
        # But this script is just a template for cPanel cron.
        # If the user configures this to run every 5 minutes, we shouldn't send it.
        # It's better for them to setup a separate cron job for the daily summary:
        # 0 20 * * * python backend/cron_daily.py 
        # For simplicity, we just leave it out of the 5 minute cron, or they can call send_daily_summary separately.

if __name__ == "__main__":
    run_jobs()
