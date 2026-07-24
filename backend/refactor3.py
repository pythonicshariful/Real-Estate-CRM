import os, glob, re

d = r'c:\Users\pytho\OneDrive\Desktop\Real-Estate-CRM\backend\app\static'
files = glob.glob(os.path.join(d, '*.html'))

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    orig = content
    
    # 1. Modals
    # Replace fixed widths
    content = re.sub(r'w-\[400px\]', 'w-[95%] sm:max-w-[400px] mx-auto', content)
    content = re.sub(r'w-\[500px\]', 'w-[95%] sm:max-w-[500px] mx-auto', content)
    content = re.sub(r'w-\[600px\]', 'w-[95%] sm:max-w-[600px] mx-auto', content)
    content = re.sub(r'\bw-96\b', 'w-[95%] sm:w-96 mx-auto', content)
    
    # 2. Add max-h to modal content forms if missing.
    # Let's just find forms inside fixed inset-0 modals
    
    # 3. Tables
    # Wrap <table ...> in <div class="overflow-x-auto w-full"> if not already inside one.
    # regex: look for <table ... </table>
    # this is safe:
    def wrap_table(match):
        table_html = match.group(0)
        return f'<div class="overflow-x-auto w-full pb-4">\n{table_html}\n</div>'
    
    # Split by <div class="overflow-x-auto to avoid double wrapping
    # Better yet, just find all <table... and replace them if we don't see overflow-x-auto in the 50 chars before
    parts = re.split(r'(<table[^>]*>)', content)
    new_content = ""
    for i, p in enumerate(parts):
        if p.startswith('<table'):
            # check previous part
            if 'overflow-x-auto' not in new_content[-100:]:
                new_content += '<div class="overflow-x-auto w-full pb-4">\n' + p
            else:
                new_content += p
        else:
            if i > 0 and parts[i-1].startswith('<table'):
                # find the end of the table
                # actually split keeps the delimiter. parts[i] contains everything up to the NEXT table.
                # we just need to replace </table> with </table>\n</div> if we wrapped it.
                pass
            new_content += p
            
    # Simpler regex for table wrapping:
    # First, temporarily remove existing wrappers so we can unify them
    content = re.sub(r'<div class="overflow-x-auto[^>]*>\s*(<table.*?</table\s*>)\s*</div>', r'\1', content, flags=re.DOTALL | re.IGNORECASE)
    # Then wrap all tables
    content = re.sub(r'(<table.*?</table\s*>)', r'<div class="overflow-x-auto w-full">\n\1\n</div>', content, flags=re.DOTALL | re.IGNORECASE)

    if content != orig:
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f'Updated {os.path.basename(f)}')
