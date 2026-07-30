import os
import glob
import re

files = glob.glob('c:/Users/pytho/OneDrive/Desktop/Real-Estate-CRM/backend/app/blueprints/**/*.py', recursive=True)

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    if '_is_admin(role)' in content:
        # replace function definition (varies slightly)
        content = re.sub(r'def _is_admin\(role\):\s*return role == [^\n]+\n', '', content)
        
        # replace calls
        content = content.replace('_is_admin(role)', 'has_role(role, UserRole.ADMIN)')
        
        # ensure import
        if 'has_role' not in content:
            content = content.replace('from flask import', 'from app.utils.rbac import has_role\nfrom flask import', 1)
            
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {file}")
