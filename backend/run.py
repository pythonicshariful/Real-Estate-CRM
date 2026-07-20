"""
run.py — Local development server.
Run with: python run.py
(NOT for production — use passenger_wsgi.py or wsgi.py instead)
"""

import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app

app = create_app(os.environ.get('FLASK_CONFIG', 'development'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
