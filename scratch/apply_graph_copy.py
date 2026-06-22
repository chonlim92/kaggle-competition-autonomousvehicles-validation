import re

with open('src/agent/app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update SVG get_group to use class instead of onclick
get_group_new = '''
    def get_group(node_id, x, y, w, h, rx, fill, text_x, text_y, text_anchor, font_size, label):
        import json
        j = json.dumps(node_details[node_id]).replace('"', '&quot;')

        return f"""
        <g class="graph-node" data-json="{j}" style="cursor:pointer">
            <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="#34d399" stroke-width="2"/>
            <text x="{text_x}" y="{text_y}" fill="#a7f3d0" font-size="{font_size}" text-anchor="{text_anchor}">{label}</text>
        </g>
        """
'''
text = re.sub(r'    def get_group.*?return f"""\n.*?<g data-json=.*?"""', get_group_new.strip(), text, flags=re.DOTALL)

# 2. Update demo.load JS to include global click listener
dark_js_new = """() => {
    document.documentElement.classList.add('dark');
    document.body.classList.add('dark');
    document.addEventListener('click', (e) => {
        let node = e.target.closest('g.graph-node');
        if (node) {
            let data = node.getAttribute('data-json');
            if (data) {
                let viewer = document.getElementById('node-json-viewer');
                if (viewer) {
                    viewer.innerHTML = '<pre style="color:#a7f3d0; background:transparent; padding:15px; overflow-x:auto; margin:0;">' + JSON.stringify(JSON.parse(data), null, 2) + '</pre>';
                }
            }
        }
    });
}"""
text = re.sub(r'js="\(\) => \{ document\.documentElement.*? \}"', 'js="""' + dark_js_new + '"""', text, flags=re.DOTALL)


# 3. Add copy buttons for all textboxes
text = text.replace(
    'tab1_raw_log = gr.Textbox(label="Generated Raw Log [ RAW — CONTAINS PII — DO NOT FORWARD TO LLM ]", interactive=False)',
    'tab1_raw_log = gr.Textbox(label="Generated Raw Log [ RAW — CONTAINS PII — DO NOT FORWARD TO LLM ]", interactive=False)\n            tab1_copy_btn1 = gr.Button("📋 Copy Raw Log", size="sm")\n            tab1_copy_btn1.click(fn=None, inputs=[tab1_raw_log], outputs=[], js="(text) => { navigator.clipboard.writeText(text); }")'
)

text = text.replace(
    'tab1_pii_ground_truth = gr.Textbox(label="Injected PII Ground Truth [ Evaluation Reference ]", interactive=False)',
    'tab1_pii_ground_truth = gr.Textbox(label="Injected PII Ground Truth [ Evaluation Reference ]", interactive=False)\n            tab1_copy_btn2 = gr.Button("📋 Copy Ground Truth", size="sm")\n            tab1_copy_btn2.click(fn=None, inputs=[tab1_pii_ground_truth], outputs=[], js="(text) => { navigator.clipboard.writeText(text); }")'
)

text = text.replace(
    'tab2_purified_context = gr.Textbox(label="Purified Context [ SECURE — SAFE FOR LLM ]", interactive=False)',
    'tab2_purified_context = gr.Textbox(label="Purified Context [ SECURE — SAFE FOR LLM ]", interactive=False)\n            tab2_copy_btn1 = gr.Button("📋 Copy Purified Context", size="sm")\n            tab2_copy_btn1.click(fn=None, inputs=[tab2_purified_context], outputs=[], js="(text) => { navigator.clipboard.writeText(text); }")'
)

text = text.replace(
    'tab2_report = gr.Textbox(label="Formal Compliance Report [ FINAL OUTPUT ]", interactive=False)',
    'tab2_report = gr.Textbox(label="Formal Compliance Report [ FINAL OUTPUT ]", interactive=False)\n            tab2_copy_btn2 = gr.Button("📋 Copy Report", size="sm")\n            tab2_copy_btn2.click(fn=None, inputs=[tab2_report], outputs=[], js="(text) => { navigator.clipboard.writeText(text); }")'
)


with open('src/agent/app.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated app successfully")
