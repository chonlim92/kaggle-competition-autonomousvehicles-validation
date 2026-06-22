# User Instructions

Welcome to the Autonomous Vehicles Disengagement Validation Portal! This document will guide you through starting the backend evaluation processes and interacting with the enterprise Frontend GUI dashboard.

## Prerequisites
Ensure your local environment has the required dependencies installed:
```bash
pip install -e .[dev]
```
You will also need a valid Gemini API key. Ensure `GEMINI_API_KEY` is set in your `.env` file or directly exported in your terminal environment.

## 1. Running the Automated Evaluation Suite
Before launching the frontend, you can verify the pipeline's robustness against our Ground Truth dataset by running the trajectory evaluation test suite:

```bash
pytest tests/evaluation/ -v
```
This runs the `adk eval` equivalent evaluation scripts and constraint enforcement unit tests to ensure guardrails and RAG retrievals are performing as expected.

## 2. Launching the Enterprise Dashboard (Gradio Frontend)
The portal is served locally using Gradio. To launch the application, run the following command from the root of the project:

```bash
python src/agent/app.py
```

Upon executing this command, a local web server will spin up. Look for an output in your terminal similar to:
`Running on local URL:  http://127.0.0.1:7861/`

Open this URL in your web browser to access the portal.

## 3. Navigating the Dashboard
The Enterprise Dashboard is split into three main tabs, allowing you to seamlessly progress from data generation to analysis.

### Tab 1: Synthetic Data Generation Engine
1. **Purpose:** This tab allows you to procedurally generate messy, realistic disengagement logs to test the downstream system.
2. **Action:** Click the **"Generate Log"** button.
3. **Result:** The system will use Gemini 3.5 Flash to synthesize a highly complex scenario involving heavy traffic, sensor obstructions, and injected Personal Identifiable Information (PII) like Driver Names, Plates, and GPS Coordinates.

### Tab 2: Secure Validation Audit Portal
1. **Purpose:** This is the core operational area where raw logs are scrubbed and formally analyzed against corporate guardrails.
2. **Action:**
   - Paste a raw log (or the synthetic one generated from Tab 1) into the **"Raw Input Field Notes"** text box.
   - Click the **"Process and Analyze Log"** button.
3. **Result:**
   - **Stage 1 (Client-Side Scrubbing):** The raw log will first be processed locally. You will see the scrubbed text in the "Purified Outbound Prompt Context" box, verifying that all PII was intercepted and replaced with safe tags (e.g., `[DRIVER_REDACTED]`).
   - **Stage 2 (Compliance Analysis):** The scrubbed text is sent securely to the Compliance Agent (Gemini 3.1 Pro). The agent will query the RAG assets, fetch Geolocation/Weather data, validate any telemetry gaps, and return a structured Kaggle-ready Compliance JSONL format detailing the incident severity. An interactive map frame will also render the incident location.

### Tab 3: Automated Performance Evaluation
1. **Purpose:** This tab acts as an on-demand audit runner to execute integration checks.
2. **Action:** Click **"Run Automated Eval Suite"**.
3. **Result:** The dashboard will execute a suite of smoke tests on the generated data. It will ensure that PII recall constraints are met, verify API integrations, and output a detailed pass/fail testing report straight to the UI.

## Support
If you encounter any issues, please ensure your GitHub API dependencies are updated and your Python environment paths are fully resolved. You can also view the GitHub Actions CI tab for continuous integration status checks.
