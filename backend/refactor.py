import os, glob, re

d = r'c:\Users\pytho\OneDrive\Desktop\Real-Estate-CRM\backend\app\static'
files = glob.glob(os.path.join(d, '*.html'))

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    orig = content
    
    # 1. Header flex-wrap
    content = re.sub(
        r'(<header[^>]*class="[^"]*flex items-center justify-between)([^"]*)(">)',
        lambda m: m.group(1) + (m.group(2) if 'flex-wrap' in m.group(2) else m.group(2) + ' flex-wrap gap-3') + m.group(3),
        content
    )
    
    # 2. Modals - replace fixed widths with responsive widths
    content = re.sub(r'w-\[400px\]', 'w-[95%] sm:max-w-[400px] mx-auto', content)
    content = re.sub(r'w-\[500px\]', 'w-[95%] sm:max-w-[500px] mx-auto', content)
    content = re.sub(r'w-\[600px\]', 'w-[95%] sm:max-w-[600px] mx-auto', content)
    content = re.sub(r'w-96(?!\w)', 'w-[95%] sm:w-96 mx-auto', content) # only word boundary
    
    # Add max-h and overflow to modal bodies to ensure scrollability on mobile
    content = re.sub(r'(class="[^"]*p-6[^"]*)(">\s*<h2)', r'\1 max-h-[90vh] overflow-y-auto\2', content)

    # 3. Tables - wrap tables with overflow-x-auto
    # We find <table and check if we are inside a div with overflow-x-auto
    # A simple but reliable way is to find <table class="..."> and replace it with <div class="overflow-x-auto w-full"><table class="..."> and then replace </table> with </table></div>
    # But ONLY if it is not already preceded by overflow-x-auto
    
    parts = content.split('<table')
    if len(parts) > 1:
        new_content = parts[0]
        for i in range(1, len(parts)):
            part = parts[i]
            # check the end of the previous part
            prev_tail = new_content[-100:]
            if 'overflow-x-auto' not in prev_tail:
                new_content += '<div class="overflow-x-auto w-full max-w-[100vw]">\n            <table' + part
                # now we need to find the corresponding </table> in this part and add </div> after it
                # this relies on </table> being present
                if '</table>' in new_content:
                    # actually wait, it's easier to just do a string replace on </table> for that specific block
                    pass
            else:
                new_content += '<table' + part
        # this split/join is too fragile.
        pass

    # Safe regex for table wrap:
    # We look for <table ...> ... </table>
    # We use re.sub with a function to check if it's already wrapped.
    def wrap_table(m):
        full_match = m.group(0)
        return f'<div class="overflow-x-auto w-full pb-4">{full_match}</div>'

    # find all tables
    # we need re.DOTALL to match across lines
    tables = re.finditer(r'<table.*?</table\s*>', content, re.DOTALL | re.IGNORECASE)
    # this might be tricky to replace in place safely if there are nested tables (unlikely here)
    # let's just do it manually for tables since there are only about 10 files with tables.

    if content != orig:
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f'Updated {os.path.basename(f)}')
