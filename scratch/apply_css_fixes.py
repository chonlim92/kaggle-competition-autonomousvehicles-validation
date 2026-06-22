import re

with open('src/agent/app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update Custom CSS
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

text = text.replace('/* ── Status indicator ──────────────────────────────────────────── */', css_addition + '\n/* ── Status indicator ──────────────────────────────────────────── */')

# 2. Fix the tabs titles
text = text.replace('with gr.Tab("🛡️ 2. Secure Validation Audit Portal"):', 'with gr.Tab(" 2. Secure Validation Audit Portal"):')
text = text.replace('with gr.Tab(" 🛡️ 2. Secure Validation Audit Portal"):', 'with gr.Tab(" 2. Secure Validation Audit Portal"):')
text = text.replace('with gr.Tab("⚡ 1. Synthetic Data Generation Engine"):', 'with gr.Tab(" 1. Synthetic Data Generation Engine"):')

# Write back
with open('src/agent/app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Applied CSS patches and Tab renaming!')
