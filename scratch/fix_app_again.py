import re

with open('src/agent/app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Add show_copy_button=True to Textboxes
text = re.sub(r'(gr\.Textbox\([^)]*label=[^)]*)(?<!show_copy_button=True)(\s*\))', r'\1, show_copy_button=True\2', text, flags=re.DOTALL)

# Let's fix tabs and missing copy buttons in CSS
css_fix = """
/* Override Gradio CSS Variables for Tabs and Copy Buttons */
:root, .dark, body {
    --tab-text-color: #ffffff !important;
    --tab-text-color-active: #ffffff !important;
    --tab-text-color-hover: #ffffff !important;
    --block-title-text-color: #ffffff !important;
    --body-text-color-subdued: #ffffff !important;
}
.tab-nav button { color: #ffffff !important; }
.tabitem > div { color: #ffffff !important; }

/* Ensure copy buttons are visible */
button.copy_button, button.copy-button {
    display: inline-flex !important;
    color: #ffffff !important;
    opacity: 1 !important;
    visibility: visible !important;
}
svg.copy-icon {
    stroke: #ffffff !important;
    fill: none !important;
}
"""

text = re.sub(r'(_CUSTOM_CSS\s*=\s*\"\"\")', r'\1\n' + css_fix, text, count=1)

with open('src/agent/app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Applied copy button fix and tab CSS variables.')
