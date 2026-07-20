"""
wsgi.py — PythonAnywhere Entry Point
======================================
This file is used by PythonAnywhere's WSGI configuration.

SETUP INSTRUCTIONS FOR PythonAnywhere:
1. Upload all files in /backend/ to your PythonAnywhere home directory
   (e.g., /home/yourusername/crmforsouth/)
2. In PythonAnywhere → Web → Add a new web app:
   - Choose: Manual configuration
   - Python version: 3.11
3. In the WSGI configuration file (click the link shown), replace ALL content
   with the code below (or just point it to this file):

   import sys
   sys.path.insert(0, '/home/yourusername/crmforsouth')
   from wsgi import application

4. In PythonAnywhere → Web → Environment variables, add all your .env values
5. In PythonAnywhere → Consoles, open a Bash console and run:
   cd /home/yourusername/crmforsouth
   pip3 install --user -r requirements.txt
   flask db upgrade
   flask create-admin

See DEPLOYMENT_PYTHONANYWHERE.md for full instructions.
"""

import sys
import os

# ← CHANGE THIS to your actual PythonAnywhere username and folder
PROJECT_DIR = '/home/YOURUSERNAME/crmforsouth'

sys.path.insert(0, PROJECT_DIR)

# Load .env
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_DIR, '.env'))

os.environ.setdefault('FLASK_CONFIG', 'production')

from app import create_app

application = create_app('production')
