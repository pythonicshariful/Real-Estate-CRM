import os
import glob

files = glob.glob('c:/Users/pytho/OneDrive/Desktop/Real-Estate-CRM/backend/app/blueprints/**/*.py', recursive=True)

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    changed = False
    
    if 'has_role(role, UserRole.ADMIN)' in content:
        content = content.replace('has_role(role, UserRole.ADMIN)', 'is_admin(role)')
        changed = True
        
    if 'from app.utils.rbac import has_role' in content:
        content = content.replace('from app.utils.rbac import has_role', 'from app.utils.rbac import is_admin')
        changed = True

    if changed:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {file}")
