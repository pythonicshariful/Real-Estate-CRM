"""
passenger_wsgi.py — cPanel Entry Point
=======================================
This file is used by cPanel's Passenger/WSGI to start the Flask app.

SETUP INSTRUCTIONS FOR cPanel:
1. Upload all files in /backend/ to your cPanel home directory
   (e.g., /home/yourusername/crmforsouth/)
2. In cPanel → Python App, set:
   - Python version: 3.11 or 3.12
   - Application root: /home/yourusername/crmforsouth
   - Application URL: your domain or subdomain
   - Application startup file: passenger_wsgi.py
   - Application Entry point: application
3. Set environment variables in cPanel → Python App → Environment Variables
4. Click "Run pip install" and paste your requirements.txt contents
5. Restart the app

See DEPLOYMENT_CPANEL.md for full instructions.
"""

import sys
import os

# Add the backend directory to Python path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

# Load .env file (cPanel doesn't auto-load .env)
from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, '.env'))

# Set the Flask config to production
os.environ.setdefault('FLASK_CONFIG', 'production')

# Import and create the app
from app import create_app

application = create_app('production')

# Passenger requires the variable to be named 'application'
if __name__ == '__main__':
    application.run()
