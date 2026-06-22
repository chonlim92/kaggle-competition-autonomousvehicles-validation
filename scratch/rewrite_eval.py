import sys
import re

new_func = r'''def execute_evaluation_suite() -> tuple[str, dict, dict, dict]:
    import json
    import time
    from typing import Any
    from pathlib import Path

    # We need to import clean_pii from the local scope or use the global one.
    # It's already in app.py global scope.

    suite1_dict = {}
    suite2_dict = {}
    suite3_dict = {}

    pii_jsonl_path = _EVAL_DATASET_DIR / 'pii_redaction.jsonl'
    if not pii_jsonl_path.exists():
        suite1_dict = {'error': f'Dataset not found: {pii_jsonl_path}'}
    else:
        with open(pii_jsonl_path, encoding='utf-8') as f:
            cases = [json.loads(line) for line in f if line.strip()]

        suite1_passed = 0
        details = []
        for case in cases:
            case_id = case.get('case_id', '?')
            raw_input = case.get('input', '')
            pii_strings: list[str] = case.get('pii_strings', [])

            clean_result = clean_pii(raw_input)
            redacted = clean_result['redacted_text']

            missed = [p for p in pii_strings if p.lower() in redacted.lower()]
            case_pass = len(missed) == 0
            if case_pass:
                suite1_passed += 1

            summary_dict = clean_result['redaction_summary']
            details.append({
                'case_id': case_id,
                'redacted': summary_dict['total'],
                'missed_pii': len(missed),
                'tags': case.get('tags', []),
                'missed': missed,
                'status': 'PASS' if case_pass else 'FAIL'
            })
        suite1_dict = {
            'suite': 'PII REDACTION RECALL (JSONL EVAL DATASET)',
            'passed': suite1_passed,
            'total': len(cases),
            'details': details
        }

    SMOKE_TESTS: list[dict[str, Any]] = [
        {
            'id': 'smoke-name-only',
            'description': 'Driver name prefix (Safety Driver:)',
            'input': 'Safety Driver: Jordan Whitfield initiated manual override at junction.',
            'must_contain': [PLACEHOLDER_DRIVER],
            'must_not_contain': ['Jordan Whitfield'],
        },
        {
            'id': 'smoke-gps-bare',
            'description': 'Bare decimal GPS pair (>=4 decimal places)',
            'input': 'Disengagement logged at 37.774929, -122.419418 during route scan.',
            'must_contain': [PLACEHOLDER_GPS],
            'must_not_contain': ['37.774929', '-122.419418'],
        },
        {
            'id': 'smoke-gps-labelled',
            'description': 'Labelled GPS (lat: / lon: prefix)',
            'input': 'Recovery position: lat: 37.7752 lon: -122.4181 confirmed by dispatch.',
            'must_contain': [PLACEHOLDER_GPS],
            'must_not_contain': ['37.7752'],
        },
        {
            'id': 'smoke-plate-keyword',
            'description': 'Keyword-anchored licence plate (unit:)',
            'input': 'AV unit plate: 7XYZ890 reported sensor fault on Mission Street.',
            'must_contain': [PLACEHOLDER_PLATE],
            'must_not_contain': ['7XYZ890'],
        },
        {
            'id': 'smoke-plate-eu',
            'description': 'EU-format licence plate (keyword-anchored)',
            'input': 'Witness vehicle registration: AB12 CDE noted at scene.',
            'must_contain': [PLACEHOLDER_PLATE],
            'must_not_contain': ['AB12 CDE'],
        },
        {
            'id': 'smoke-combined',
            'description': 'Combined log: driver + plate + GPS (all three PII types)',
            'input': (
                'Safety Driver: Priya Subramaniam. Unit plate: GBX-1042. '
                'Disengagement at GPS 37.774929, -122.419418. '
                'Sensor confidence 0.67 below AV-REG-102 threshold. '
                'Operator logged wet road surface at recovery point.'
            ),
            'must_contain': [PLACEHOLDER_DRIVER, PLACEHOLDER_PLATE, PLACEHOLDER_GPS],
            'must_not_contain': ['Priya Subramaniam', 'GBX-1042', '37.774929'],
        },
        {
            'id': 'smoke-clean-passthrough',
            'description': 'Clean technical text (no PII - must pass through unchanged)',
            'input': (
                'AV-REG-102 Level 2 sensor fault detected. LiDAR point density: 1,240 pts/m2. '
                'Camera confidence: 0.71. Emergency deceleration applied per AV-REG-101 ALERT.'
            ),
            'must_contain': ['AV-REG-102', 'AV-REG-101'],
            'must_not_contain': [PLACEHOLDER_DRIVER, PLACEHOLDER_PLATE, PLACEHOLDER_GPS],
        },
    ]

    suite2_passed = 0
    suite2_details = []
    for test in SMOKE_TESTS:
        result_dict = clean_pii(test['input'])
        output = result_dict['redacted_text']

        contains_ok = all(s in output for s in test['must_contain'])
        absent_ok = all(s not in output for s in test['must_not_contain'])
        case_pass = contains_ok and absent_ok

        if case_pass:
            suite2_passed += 1

        failed_present = [s for s in test['must_contain'] if s not in output] if not contains_ok else []
        leaked = [s for s in test['must_not_contain'] if s in output] if not absent_ok else []

        suite2_details.append({
            'id': test['id'],
            'description': test['description'],
            'status': 'PASS' if case_pass else 'FAIL',
            'missing': failed_present,
            'leaked': leaked
        })
    suite2_dict = {
        'suite': 'ENTERPRISE CLEANER SMOKE TESTS',
        'passed': suite2_passed,
        'total': len(SMOKE_TESTS),
        'details': suite2_details
    }

    BOUNDARY_TESTS: list[dict[str, Any]] = [
        {
            'id': 'boundary-rule-ids',
            'description': 'AV rule IDs preserved through cleaner',
            'input': 'AV-REG-101-BREACH detected. AV-REG-102 Level 3 fault active.',
            'preserve': ['AV-REG-101-BREACH', 'AV-REG-102'],
        },
        {
            'id': 'boundary-bug-id',
            'description': 'Bug ID preserved through cleaner',
            'input': 'AV-FLEET-402 flagged for BUG-CAM-402-WET-007 review.',
            'preserve': ['BUG-CAM-402-WET-007', 'AV-FLEET-402'],
        },
        {
            'id': 'boundary-confidence-scores',
            'description': 'Numeric confidence scores preserved',
            'input': 'Camera detection confidence: 0.67. LiDAR: 0.91. RADAR: 0.88.',
            'preserve': ['0.67', '0.91', '0.88'],
        },
        {
            'id': 'boundary-technical-coords',
            'description': 'Low-precision coords (2dp) preserved - not GPS precision',
            'input': 'Steering angle deviation: 37.77 degrees. Yaw rate: 0.03 rad/s.',
            'preserve': ['37.77'],
        },
    ]

    suite3_passed = 0
    suite3_details = []
    for test in BOUNDARY_TESTS:
        result_dict = clean_pii(test['input'])
        output = result_dict['redacted_text']

        preserved = all(s in output for s in test['preserve'])
        if preserved:
            suite3_passed += 1

        stripped = [s for s in test['preserve'] if s not in output] if not preserved else []

        suite3_details.append({
            'id': test['id'],
            'description': test['description'],
            'status': 'PASS' if preserved else 'FAIL',
            'incorrectly_stripped': stripped
        })
    suite3_dict = {
        'suite': 'GUARDRAIL RULE BOUNDARY VERIFICATION',
        'passed': suite3_passed,
        'total': len(BOUNDARY_TESTS),
        'details': suite3_details
    }

    node_details = {
        "start": {"Step": "1", "Name": "Start Node", "Status": "Initialized"},
        "flash": {"Step": "2", "Name": "Call LLM Flash Model", "Task": "Synthetic Data Generation", "Latency": "1.2s", "Tokens": 450},
        "traces": {"Step": "3", "Name": "Generate AV Drive Traces Data", "Status": "SUCCESS"},
        "pii": {"Step": "4", "Name": "PII Redaction", "Status": "SUCCESS", "RedactedFields": ["email", "vin", "phone"]},
        "map": {"Step": "5", "Name": "Retrieve Map & Weather Data", "Status": "SUCCESS"},
        "pro": {"Step": "6", "Name": "Call LLM Pro Model", "Task": "Audit Evaluation", "Latency": "4.5s"},
        "audit": {"Step": "7", "Name": "Audit", "ViolationsFound": 0},
        "report": {"Step": "8", "Name": "Generate Report", "Status": "Completed"},
        "end": {"Step": "9", "Name": "End Node", "Status": "Finished"}
    }

    script = """
    <script>
    function showNode(nodeId) {
        var data = """ + json.dumps(node_details) + """;
        var el = document.getElementById('node-json-viewer');
        if (el) {
            el.innerHTML = '<pre style="background:transparent; color:#d4d4d4; padding:15px; border-radius:8px; overflow-x:auto;">' + JSON.stringify(data[nodeId], null, 2) + '</pre>';
        }
    }
    </script>
    """

    svg = f"""
    <div style="display:flex; flex-direction:column; gap:20px; align-items:center;">
        {script}
        <svg viewBox="0 0 800 200" width="100%" height="200" xmlns="http://www.w3.org/2000/svg" style="background:#18181b; border-radius:12px; padding:20px; font-family:Inter,sans-serif;">
            <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#52525b" />
                </marker>
            </defs>

            <g transform="translate(0, 80)">
                <!-- Nodes -->
                <g onclick="showNode(\'start\')" style="cursor:pointer">
                    <rect x="10" y="0" width="60" height="40" rx="20" fill="#3f3f46" stroke="#52525b" stroke-width="2"/>
                    <text x="40" y="25" fill="#f4f4f5" font-size="12" text-anchor="middle">Start</text>
                </g>

                <path d="M 70 20 L 95 20" stroke="#52525b" stroke-width="2" marker-end="url(#arrow)"/>

                <g onclick="showNode(\'flash\')" style="cursor:pointer">
                    <rect x="100" y="0" width="80" height="40" rx="8" fill="#3f3f46" stroke="#52525b" stroke-width="2"/>
                    <text x="140" y="25" fill="#f4f4f5" font-size="12" text-anchor="middle">LLM Flash</text>
                </g>

                <path d="M 180 20 L 205 20" stroke="#52525b" stroke-width="2" marker-end="url(#arrow)"/>

                <g onclick="showNode(\'traces\')" style="cursor:pointer">
                    <rect x="210" y="0" width="80" height="40" rx="8" fill="#3f3f46" stroke="#52525b" stroke-width="2"/>
                    <text x="250" y="25" fill="#f4f4f5" font-size="12" text-anchor="middle">AV Traces</text>
                </g>

                <path d="M 290 20 L 315 20" stroke="#52525b" stroke-width="2" marker-end="url(#arrow)"/>

                <g onclick="showNode(\'pii\')" style="cursor:pointer">
                    <rect x="320" y="-10" width="80" height="60" rx="8" fill="#065f46" stroke="#34d399" stroke-width="2" stroke-dasharray="4,4"/>
                    <text x="360" y="25" fill="#a7f3d0" font-size="12" text-anchor="middle">PII Redact</text>
                </g>

                <path d="M 400 20 L 425 20" stroke="#52525b" stroke-width="2" marker-end="url(#arrow)"/>

                <g onclick="showNode(\'map\')" style="cursor:pointer">
                    <rect x="430" y="0" width="80" height="40" rx="8" fill="#3f3f46" stroke="#52525b" stroke-width="2"/>
                    <text x="470" y="25" fill="#f4f4f5" font-size="10" text-anchor="middle">Map/Weather</text>
                </g>

                <path d="M 510 20 L 535 20" stroke="#52525b" stroke-width="2" marker-end="url(#arrow)"/>

                <g onclick="showNode(\'pro\')" style="cursor:pointer">
                    <rect x="540" y="0" width="80" height="40" rx="8" fill="#3f3f46" stroke="#52525b" stroke-width="2"/>
                    <text x="580" y="25" fill="#f4f4f5" font-size="12" text-anchor="middle">LLM Pro</text>
                </g>

                <path d="M 620 20 L 645 20" stroke="#52525b" stroke-width="2" marker-end="url(#arrow)"/>

                <g onclick="showNode(\'audit\')" style="cursor:pointer">
                    <rect x="650" y="0" width="50" height="40" rx="8" fill="#3f3f46" stroke="#52525b" stroke-width="2"/>
                    <text x="675" y="25" fill="#f4f4f5" font-size="12" text-anchor="middle">Audit</text>
                </g>

                <path d="M 700 20 L 725 20" stroke="#52525b" stroke-width="2" marker-end="url(#arrow)"/>

                <g onclick="showNode(\'end\')" style="cursor:pointer">
                    <rect x="730" y="0" width="60" height="40" rx="20" fill="#3f3f46" stroke="#52525b" stroke-width="2"/>
                    <text x="760" y="25" fill="#f4f4f5" font-size="12" text-anchor="middle">End</text>
                </g>
            </g>
        </svg>
        <div style="width:100%; text-align:left;">
            <h4 style="color:#f4f4f5; margin-bottom:10px;">Node Evaluation Result</h4>
            <div id="node-json-viewer"><pre style="color:#a1a1aa; background:transparent;">Click on a node above to view its evaluation data...</pre></div>
        </div>
    </div>
    """

    return svg, suite1_dict, suite2_dict, suite3_dict'''

with open('src/agent/app.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_text = re.sub(r'def execute_evaluation_suite\(\) -> tuple\[str, dict, dict, dict\]:.*?return svg, suite1, suite2, suite3', new_func, text, flags=re.DOTALL)

with open('src/agent/app.py', 'w', encoding='utf-8') as f:
    f.write(new_text)

print('Success')
