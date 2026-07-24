import os, glob

d = r'c:\Users\pytho\OneDrive\Desktop\Real-Estate-CRM\backend\app\static'
files = glob.glob(os.path.join(d, '*.html'))

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    orig = content

    # Fix fixed-width modals - don't replace if already replaced
    if 'w-[95%]' not in content:
        content = content.replace('w-[500px]', 'w-[95%] sm:w-[500px] mx-auto')
        content = content.replace('w-[600px]', 'w-[95%] sm:w-[600px] mx-auto')
        content = content.replace('w-[400px]', 'w-[95%] sm:w-[400px] mx-auto')
        content = content.replace('w-96', 'w-[95%] sm:w-96 mx-auto')
    
    # Fix tables
    if '<table ' in content and 'overflow-x-auto' not in content:
        content = content.replace('<table ', '<div class="overflow-x-auto w-full">\n<table ')
        content = content.replace('</table>', '</table>\n</div>')
        
    # Fix headers
    content = content.replace(
        'justify-between px-4 md:px-6 z-10 flex-shrink-0">',
        'justify-between px-4 md:px-6 z-10 flex-shrink-0 flex-wrap gap-3">'
    )
    content = content.replace(
        'justify-between px-4 md:px-6 flex-shrink-0">',
        'justify-between px-4 md:px-6 flex-shrink-0 flex-wrap gap-3">'
    )
    
    if content != orig:
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f'Updated {os.path.basename(f)}')
