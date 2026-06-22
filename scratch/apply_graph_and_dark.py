import re

with open('src/agent/app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Fix SVG Graph Click Handlers (proper data-json attribute approach)
new_graph_code = '''
    node_details = {
        "start": {"Step": "1", "Name": "Start Node", "Status": "Initialized", "Eval": "Pass"},
        "flash": {"Step": "2", "Name": "Call LLM Flash Model", "Task": "Synthetic Data Generation", "Latency": "1.2s", "Tokens": 450, "Eval": "Pass"},
        "traces": {"Step": "3", "Name": "Generate AV Drive Traces Data", "Status": "SUCCESS", "Eval": "Pass"},
        "pii": {"Step": "4", "Name": "PII Redaction", "Status": "SUCCESS", "RedactedFields": ["email", "vin", "phone"], "Eval": "Pass"},
        "map": {"Step": "5", "Name": "Retrieve Map & Weather Data", "Status": "SUCCESS", "Eval": "Pass"},
        "pro": {"Step": "6", "Name": "Call LLM Pro Model", "Task": "Audit Evaluation", "Latency": "4.5s", "Eval": "Pass"},
        "audit": {"Step": "7", "Name": "Audit", "ViolationsFound": 0, "Eval": "Pass"},
        "report": {"Step": "8", "Name": "Generate Report", "Status": "Completed", "Eval": "Pass"},
        "end": {"Step": "9", "Name": "End Node", "Status": "Finished", "Eval": "Pass"}
    }

    def get_group(node_id, x, y, w, h, rx, fill, text_x, text_y, text_anchor, font_size, label):
        import json
        j = json.dumps(node_details[node_id]).replace('"', '&quot;')
        onclick_script = "document.getElementById('node-json-viewer').innerHTML='<pre style=\\'color:#a7f3d0; background:transparent; padding:15px; overflow-x:auto; margin:0;\\'>' + JSON.stringify(JSON.parse(this.getAttribute('data-json')), null, 2) + '</pre>'"

        return f"""
        <g data-json="{j}" onclick="{onclick_script}" style="cursor:pointer">
            <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="#34d399" stroke-width="2"/>
            <text x="{text_x}" y="{text_y}" fill="#a7f3d0" font-size="{font_size}" text-anchor="{text_anchor}">{label}</text>
        </g>
        """

    svg = f"""
    <div style="display:flex; flex-direction:column; gap:20px; align-items:center;">
        <svg viewBox="0 0 800 200" width="100%" height="200" xmlns="http://www.w3.org/2000/svg" style="background:#18181b; border-radius:12px; padding:20px; font-family:Inter,sans-serif;">
            <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#34d399" />
                </marker>
            </defs>

            <g transform="translate(0, 80)">
                {get_group('start', 10, 0, 60, 40, 20, '#065f46', 40, 25, 'middle', 12, 'Start')}
                <path d="M 70 20 L 95 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                {get_group('flash', 100, 0, 80, 40, 8, '#065f46', 140, 25, 'middle', 12, 'LLM Flash')}
                <path d="M 180 20 L 205 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                {get_group('traces', 210, 0, 80, 40, 8, '#065f46', 250, 25, 'middle', 12, 'AV Traces')}
                <path d="M 290 20 L 315 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                {get_group('pii', 320, -10, 80, 60, 8, '#065f46', 360, 25, 'middle', 12, 'PII Redact')}
                <path d="M 400 20 L 425 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                {get_group('map', 430, 0, 80, 40, 8, '#065f46', 470, 25, 'middle', 10, 'Map/Weather')}
                <path d="M 510 20 L 535 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                {get_group('pro', 540, 0, 80, 40, 8, '#065f46', 580, 25, 'middle', 12, 'LLM Pro')}
                <path d="M 620 20 L 645 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                {get_group('audit', 650, 0, 50, 40, 8, '#065f46', 675, 25, 'middle', 12, 'Audit')}
                <path d="M 700 20 L 725 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                {get_group('end', 730, 0, 60, 40, 20, '#065f46', 760, 25, 'middle', 12, 'End')}
            </g>
        </svg>
        <div style="width:100%; text-align:left;">
            <h4 style="color:#f4f4f5; margin-bottom:10px;">Node Evaluation Result</h4>
            <div id="node-json-viewer" style="background:#18181b; border:1px solid #3f3f46; border-radius:8px; min-height:80px; padding:10px;"><pre style="color:#a1a1aa; background:transparent; margin:0;">Click on a node above to view its evaluation data...</pre></div>
        </div>
    </div>
    """
'''

text = re.sub(r'    node_details = \{.*?return svg, suite1_dict, suite2_dict, suite3_dict', new_graph_code + '\n    return svg, suite1_dict, suite2_dict, suite3_dict', text, flags=re.DOTALL)


# 2. Force Dark Mode
dark_js = "() => { document.documentElement.classList.add('dark'); document.body.classList.add('dark'); }"
if 'demo.load(fn=_init_session_id' in text and 'js=' not in text:
    text = text.replace('demo.load(fn=_init_session_id, inputs=[], outputs=[session_id_state])',
                        'demo.load(fn=_init_session_id, inputs=[], outputs=[session_id_state], js="' + dark_js + '")')
elif 'demo.load(fn=_init_session_id' in text:
    text = re.sub(r'demo\.load\(fn=_init_session_id.*?outputs=\[session_id_state\].*?\)',
                  'demo.load(fn=_init_session_id, inputs=[], outputs=[session_id_state], js="' + dark_js + '")', text)


with open('src/agent/app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated successfully")
