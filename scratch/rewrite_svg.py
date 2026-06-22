import re

with open('src/agent/app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

# We want to replace just the svg_graph creation logic inside execute_evaluation_suite
# We will find the svg_graph definition and replace it.

old_svg_pattern = r"svg_color_s1 = .*?svg_graph = f'''(.*?)'''\n"
match = re.search(old_svg_pattern, app_code, flags=re.DOTALL)
if match:
    new_svg = """    # SVG rendering: ADK Playground style trajectory graph
    svg_graph = f'''
    <svg width="800" height="200" xmlns="http://www.w3.org/2000/svg" style="background-color: #1e1e1e; border-radius: 8px;">
      <style>
        .agent {{ fill: #166534; stroke: #22c55e; stroke-width: 2px; }}
        .tool-executed {{ fill: #064e3b; stroke: #22c55e; stroke-width: 2px; stroke-dasharray: 4; }}
        .tool-unexecuted {{ fill: #27272a; stroke: #52525b; stroke-width: 2px; }}
        .edge {{ stroke: #52525b; stroke-width: 2px; fill: none; }}
        .text-agent {{ font-family: sans-serif; font-size: 13px; font-weight: bold; fill: #ffffff; text-anchor: middle; dominant-baseline: middle; }}
        .text-executed {{ font-family: sans-serif; font-size: 12px; fill: #ffffff; text-anchor: middle; dominant-baseline: middle; }}
        .text-unexecuted {{ font-family: sans-serif; font-size: 12px; fill: #a1a1aa; text-anchor: middle; dominant-baseline: middle; }}
      </style>
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#52525b" />
        </marker>
      </defs>

      <!-- Edges -->
      <path d="M 400 60 L 400 85" class="edge" />
      <path d="M 160 85 L 640 85" class="edge" />
      <path d="M 160 85 L 160 115" class="edge" marker-end="url(#arrow)" />
      <path d="M 320 85 L 320 115" class="edge" marker-end="url(#arrow)" />
      <path d="M 480 85 L 480 115" class="edge" marker-end="url(#arrow)" />
      <path d="M 640 85 L 640 115" class="edge" marker-end="url(#arrow)" />

      <!-- Agent Node -->
      <rect x="290" y="30" width="220" height="30" rx="15" class="agent" />
      <text x="400" y="46" class="text-agent">◆ av_validation_orchestrator</text>

      <!-- Tool Nodes -->
      <rect x="90" y="120" width="140" height="30" rx="15" class="tool-executed" />
      <text x="160" y="136" class="text-executed">🔧 clean_pii</text>

      <rect x="250" y="120" width="140" height="30" rx="15" class="tool-unexecuted" />
      <text x="320" y="136" class="text-unexecuted">🔧 validate_telemetry</text>

      <rect x="410" y="120" width="140" height="30" rx="15" class="tool-unexecuted" />
      <text x="480" y="136" class="text-unexecuted">🔧 validate_labels</text>

      <rect x="570" y="120" width="140" height="30" rx="15" class="tool-unexecuted" />
      <text x="640" y="136" class="text-unexecuted">🔧 generate_report</text>
    </svg>
    '''
"""
    app_code = app_code[:match.start()] + new_svg + app_code[match.end():]
    with open('src/agent/app.py', 'w', encoding='utf-8') as f:
        f.write(app_code)
    print("SVG replaced successfully!")
else:
    print("Could not find the SVG pattern!")
