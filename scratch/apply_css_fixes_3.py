import re

with open('src/agent/app.py', 'r', encoding='utf-8') as f:
    text = f.read()

css_addition = """
/* Force Tab Texts to White */
.tab-nav button, .tab-nav button span {
    color: #ffffff !important;
}

/* Remove background tag color for code elements */
.prose code, .markdown-text code {
    background: transparent !important;
    color: #ffffff !important;
    padding: 0 !important;
    border: none !important;
}

/* Force JSON background to be transparent */
.json-container, .json-wrapper, [data-testid="json"], div.json {
    background: transparent !important;
    background-color: transparent !important;
}
"""

if '/* Force Tab Texts to White */' not in text:
    match = re.search(r'(_CUSTOM_CSS\s*=\s*\"\"\".*?)(\"\"\")', text, flags=re.DOTALL)
    if match:
        new_css = match.group(1) + css_addition + '"""'
        text = text[:match.start()] + new_css + text[match.end():]
        with open('src/agent/app.py', 'w', encoding='utf-8') as f:
            f.write(text)
        print('CSS applied.')
    else:
        print('_CUSTOM_CSS not found by regex.')
else:
    print('CSS already applied.')
