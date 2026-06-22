import re
import json

with open('src/agent/app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Fix CSS
new_css = '''
/* Override Gradio CSS Variables for Tabs and Copy Buttons */
:root, .dark, body {
    --body-text-color: #ffffff !important;
}
.tab-nav button { color: #ffffff !important; opacity: 1 !important; }
.tab-nav button.selected { color: #ffffff !important; font-weight: bold !important; }
.tab-nav button:hover { color: #ffffff !important; }

/* Ensure copy buttons are visible */
button[aria-label="Copy"] {
    display: inline-flex !important;
    color: #ffffff !important;
    opacity: 1 !important;
    visibility: visible !important;
}
button[title="Copy"] {
    display: inline-flex !important;
    color: #ffffff !important;
    opacity: 1 !important;
    visibility: visible !important;
}
'''
text = re.sub(r'# Custom CSS.*?_CUSTOM_CSS = """(.*?)"""', '# Custom CSS\n_CUSTOM_CSS = """' + new_css + '"""', text, flags=re.DOTALL)

# 2. Fix SVG Graph
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

    def get_click(node_id):
        import json
        j = json.dumps(node_details[node_id]).replace('"', '&quot;')
        return f"document.getElementById('node-json-viewer').innerHTML='<pre style=\\'color:#a7f3d0; background:transparent; padding:15px; overflow-x:auto;\\'>' + JSON.stringify(JSON.parse('{j}'), null, 2) + '</pre>'"

    svg = f"""
    <div style="display:flex; flex-direction:column; gap:20px; align-items:center;">
        <svg viewBox="0 0 800 200" width="100%" height="200" xmlns="http://www.w3.org/2000/svg" style="background:#18181b; border-radius:12px; padding:20px; font-family:Inter,sans-serif;">
            <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#34d399" />
                </marker>
            </defs>

            <g transform="translate(0, 80)">
                <g onclick="{get_click('start')}" style="cursor:pointer">
                    <rect x="10" y="0" width="60" height="40" rx="20" fill="#065f46" stroke="#34d399" stroke-width="2"/>
                    <text x="40" y="25" fill="#a7f3d0" font-size="12" text-anchor="middle">Start</text>
                </g>
                <path d="M 70 20 L 95 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                <g onclick="{get_click('flash')}" style="cursor:pointer">
                    <rect x="100" y="0" width="80" height="40" rx="8" fill="#065f46" stroke="#34d399" stroke-width="2"/>
                    <text x="140" y="25" fill="#a7f3d0" font-size="12" text-anchor="middle">LLM Flash</text>
                </g>
                <path d="M 180 20 L 205 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                <g onclick="{get_click('traces')}" style="cursor:pointer">
                    <rect x="210" y="0" width="80" height="40" rx="8" fill="#065f46" stroke="#34d399" stroke-width="2"/>
                    <text x="250" y="25" fill="#a7f3d0" font-size="12" text-anchor="middle">AV Traces</text>
                </g>
                <path d="M 290 20 L 315 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                <g onclick="{get_click('pii')}" style="cursor:pointer">
                    <rect x="320" y="-10" width="80" height="60" rx="8" fill="#065f46" stroke="#34d399" stroke-width="2" stroke-dasharray="4,4"/>
                    <text x="360" y="25" fill="#a7f3d0" font-size="12" text-anchor="middle">PII Redact</text>
                </g>
                <path d="M 400 20 L 425 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                <g onclick="{get_click('map')}" style="cursor:pointer">
                    <rect x="430" y="0" width="80" height="40" rx="8" fill="#065f46" stroke="#34d399" stroke-width="2"/>
                    <text x="470" y="25" fill="#a7f3d0" font-size="10" text-anchor="middle">Map/Weather</text>
                </g>
                <path d="M 510 20 L 535 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                <g onclick="{get_click('pro')}" style="cursor:pointer">
                    <rect x="540" y="0" width="80" height="40" rx="8" fill="#065f46" stroke="#34d399" stroke-width="2"/>
                    <text x="580" y="25" fill="#a7f3d0" font-size="12" text-anchor="middle">LLM Pro</text>
                </g>
                <path d="M 620 20 L 645 20" stroke="#34d399" stroke-width=\"2\" marker-end=\"url(#arrow)\"/>

                <g onclick="{get_click('audit')}" style="cursor:pointer">
                    <rect x="650" y="0" width="50" height="40" rx="8" fill="#065f46" stroke="#34d399" stroke-width="2"/>
                    <text x="675" y="25" fill="#a7f3d0" font-size="12" text-anchor="middle">Audit</text>
                </g>
                <path d="M 700 20 L 725 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                <g onclick="{get_click('end')}" style="cursor:pointer">
                    <rect x="730" y="0" width="60" height="40" rx="20" fill="#065f46" stroke="#34d399" stroke-width="2"/>
                    <text x="760" y="25" fill="#a7f3d0" font-size="12" text-anchor="middle">End</text>
                </g>
            </g>
        </svg>
        <div style="width:100%; text-align:left;">
            <h4 style="color:#f4f4f5; margin-bottom:10px;">Node Evaluation Result</h4>
            <div id="node-json-viewer" style="background:#18181b; border:1px solid #3f3f46; border-radius:8px; min-height:80px; padding:10px;"><pre style="color:#a1a1aa; background:transparent;">Click on a node above to view its evaluation data...</pre></div>
        </div>
    </div>
    """
'''

text = re.sub(r'    node_details = \{.*?return svg, suite1_dict, suite2_dict, suite3_dict', new_graph_code + '\n    return svg, suite1_dict, suite2_dict, suite3_dict', text, flags=re.DOTALL)

with open('src/agent/app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated successfully")
