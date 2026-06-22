import sys
import re

new_tab3 = r'''    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — Automated Performance Evaluation Suite
    # ══════════════════════════════════════════════════════════════════════════
    with gr.Tab(" 3. Automated Performance Evaluation"):

        gr.Markdown("""
        ### Automated PII Redaction & Guardrail Evaluation Suite
        Runs three test suites against the `enterprise_av_security_pii_cleaner`:
        - **Suite 1** — JSONL dataset recall tests (`tests/evaluation/datasets/pii_redaction.jsonl`)
        - **Suite 2** — Smoke tests covering each PII category in isolation and combination
        - **Suite 3** — Guardrail boundary tests verifying non-PII technical content is preserved
        """)

        # Evaluation trigger button
        with gr.Row():
            tab3_eval_btn = gr.Button(
                " Execute Trajectory & PII Leak Audit Suite",
                variant="primary",
                size="lg",
                elem_classes=["eval-btn"],
            )

        # Trajectory Visualization
        tab3_workflow_graph = gr.HTML(label="Agent Trajectory Workflow")

        gr.Markdown("### Evaluation Results")

        with gr.Accordion("Suite 1: PII Redaction Recall", open=True):
            tab3_suite1 = gr.JSON(label='Suite 1 Results')

        with gr.Accordion("Suite 2: Enterprise Cleaner Smoke Tests", open=True):
            tab3_suite2 = gr.JSON(label='Suite 2 Results')

        with gr.Accordion("Suite 3: Guardrail Boundary Verification", open=True):
            tab3_suite3 = gr.JSON(label='Suite 3 Results')

        gr.Markdown("""
        > **What passes means**: Suite 2 smoke tests cover isolated and combined PII categories.
        > Suite 3 boundary tests confirm rule IDs (AV-REG-101/102), bug IDs (BUG-CAM-402-WET-007),
        > and confidence scores are NOT accidentally stripped by the PII cleaner.
        > These tests run entirely offline — no API calls, no model inference required.
        """)

        # Wire button → backend → results textbox
        tab3_eval_btn.click(
            fn=execute_evaluation_suite,
            inputs=[],
            outputs=[tab3_workflow_graph, tab3_suite1, tab3_suite2, tab3_suite3],
        )

    # ── Initialise session ID when dashboard loads ────────────────────────────'''

with open('src/agent/app.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_text = re.sub(r'    # ══════════════════════════════════════════════════════════════════════════\n    # TAB 3.*?# ── Initialise session ID when dashboard loads ────────────────────────────', new_tab3, text, flags=re.DOTALL)

with open('src/agent/app.py', 'w', encoding='utf-8') as f:
    f.write(new_text)

print('Success rewriting Tab 3')
