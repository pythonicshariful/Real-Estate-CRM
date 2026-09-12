import os
import sys
from dotenv import load_dotenv

# Define the root and backend paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")

# Ensure both paths are in the system path so Python can find the modules
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# Load environment variables from the backend folder's .env file
env_path = os.path.join(BACKEND_ROOT, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# Force Flask into production mode for cPanel
os.environ.setdefault('FLASK_CONFIG', 'production')

# Import the application factory and create the app
from app import create_app
application = create_app('production')