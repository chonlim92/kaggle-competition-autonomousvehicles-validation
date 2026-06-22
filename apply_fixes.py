import os
import time

# --- 1. Fix app.py ---
with open('src/agent/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add Copy Button under the logs in tab 1
tab1_log_replacement = """                tab1_log_output = gr.Textbox(
                    label=" Generated Raw Log  [ RAW — CONTAINS PII — DO NOT FORWARD TO LLM ]",
                    lines=22,
                    max_lines=40,
                    placeholder=(
                        "Generated AV disengagement log will appear here...\\n\\n"
                        "Copy this text to Tab 2 → 'Paste Log Text' to run the "
                        "secure validation audit pipeline."
                    ),
                    interactive=False,
                )
                tab1_copy_btn = gr.Button("📋 Copy Raw Log Text", size="sm")
                tab1_copy_btn.click(None, inputs=[tab1_log_output], js="(text) => navigator.clipboard.writeText(text)")"""

content = content.replace('                tab1_log_output = gr.Textbox(\n                    label=" Generated Raw Log  [ RAW — CONTAINS PII — DO NOT FORWARD TO LLM ]",\n                    lines=22,\n                    max_lines=40,\n                    placeholder=(\n                        "Generated AV disengagement log will appear here...\\n\\n"\n                        "Copy this text to Tab 2 → \'Paste Log Text\' to run the "\n                        "secure validation audit pipeline."\n                    ),\n\n                    interactive=False,\n                )', tab1_log_replacement.strip())

# Add Copy Button under tab 2 report
tab2_report_replacement = """        tab2_report = gr.Markdown(
            label=" Audited Corporate Compliance Report  [ Stage 2 — gemini-1.5-pro output ]",
            value="> ⬆️ Paste a log and click **Run Safe Validation Audit** to generate the compliance report.",
        )
        tab2_copy_btn = gr.Button("📋 Copy Compliance Report", size="sm")
        tab2_copy_btn.click(None, inputs=[tab2_report], js="(text) => navigator.clipboard.writeText(text)")"""

content = content.replace('        tab2_report = gr.Markdown(\n            label=" Audited Corporate Compliance Report  [ Stage 2 — gemini-1.5-pro output ]",\n            value="> ⬆️ Paste a log and click **Run Safe Validation Audit** to generate the compliance report.",\n        )', tab2_report_replacement.strip())

# Add global CSS override for ALL text to be white!
css = '''
* {
    --body-text-color: #ffffff !important;
    --body-text-color-subdued: #ffffff !important;
    --block-title-text-color: #ffffff !important;
    --block-label-text-color: #ffffff !important;
}
p, span, div, h1, h2, h3, h4, h5, h6, button, td, th {
    color: #ffffff !important;
}
'''
if '--body-text-color: #ffffff !important;' not in content:
    content = content.replace('/* ── Global app styling ────────────────────────────────────────── */', '/* ── Global app styling ────────────────────────────────────────── */' + css)

# Make sure gemini-3.5-flash is used everywhere the user requested
content = content.replace('gemini-2.0-flash', 'gemini-3.5-flash')

with open('src/agent/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

# --- 2. Fix data_simulator.py ---
# Add a 5 second sleep to avoid 15 RPM rate limits
with open('src/skills/pii_redactor/scripts/data_simulator.py', 'r', encoding='utf-8') as f:
    sim = f.read()

sim = sim.replace('gemini-2.0-flash', 'gemini-3.5-flash')

if 'import time' not in sim:
    sim = sim.replace('import random', 'import random\\nimport time')

if 'time.sleep(5)' not in sim:
    sim = sim.replace('            return generated_log', '            time.sleep(5)\\n            return generated_log')

with open('src/skills/pii_redactor/scripts/data_simulator.py', 'w', encoding='utf-8') as f:
    f.write(sim)

print("Fixes applied successfully!")
