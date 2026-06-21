# Autonomous Vehicles Disengagement Validation Portal
### Track: Agents for Business | Workspace: Antigravity IDE

![Cover Image](C:\Users\chonlim\.gemini\antigravity-ide\brain\ffa8b89e-6b11-45bf-8279-173ed4cd36de\av_dashboard_cover_1782042855146.png)

## 1. Problem Pitch & Business Value Narrative (30 Points)
Autonomous vehicle operations generate massive arrays of unorganized, messy text logs from field test drivers daily. Manually reviewing these inputs and checking them against municipal codes, stringent regulatory safety guardrails, and complex vehicle hardware histories creates an intense administrative bottleneck. This delay holds back deployment cycles, restricts rapid prototyping, and balloons operational overhead. Furthermore, these logs frequently contain highly sensitive Personally Identifiable Information (PII) such as human driver names, license plate numbers, and exact GPS coordinates, posing significant compliance and data-leakage risks if processed without extreme care.

Our application completely automates this validation structure to tackle these problems simultaneously. Built entirely using natural language vibe coding patterns inside the Antigravity IDE, this system converts raw narrative field data into secure, audit-ready corporate compliance insights in seconds. The solution dramatically accelerates the feedback loop between testing operations and engineering fixes while guaranteeing 100% adherence to data privacy standards.

## 2. Technical Design & Multi-Agent Solution Architecture (70 Points)
This application combines an interactive Frontend GUI Control Panel (built in Gradio) with an advanced, decoupled backend ADK 2.0 multi-agent pipeline. The system leverages state-of-the-art LLMs (Gemini 1.5 Pro and Gemini 1.5 Flash) orchestrating diverse deterministic tools.

The architecture is divided into the following core subsystems:

### Procedural Synthetic SDG Engine
To facilitate end-to-end testing without exposing confidential operator information or relying on scarce real-world anomalies, the platform incorporates an on-demand Synthetic Data Generation (SDG) skill. Powered by Gemini 1.5 Flash, this simulator dynamically builds messy, highly realistic testing logs. It strategically injects placeholder PII (Names, Plates, GPS Coordinates) across varied weather and traffic scenarios, ensuring our downstream filters and evaluators are continuously tested against diverse edge cases.

### Client-Side Skill Masking & Strict Defense-In-Depth PII Redaction
We implemented a strict defense-in-depth pipeline to guarantee PII never reaches the cloud. Generated inputs are intercepted and passed through a custom standalone tool skill (`enterprise_av_security_pii_cleaner`). This deterministic, regex-driven engine aggressively scrubs out sensitive driver parameters, replacing them with typed placeholders (e.g., `[DRIVER_REDACTED]`, `[GPS_REDACTED]`) before any data leaves the local infrastructure. This ensures absolute privacy compliance (GR-LEAK).

### Sequential Orchestration & RAG Knowledge Integration
The purified, redacted text passes into the orchestration layer where specialized Legal Auditor and Technical Analyst personas resolve rules intersections. Using dynamic Knowledge Retrieval (RAG) capabilities, the agent dynamically fetches domain glossaries, fleet hardware histories, and complex safety guardrails from local assets. Additionally, the orchestrator has tools to invoke third-party APIs (Google Maps Geocoding, Roads APIs for Speed Limits, and Open-Meteo for weather) to enrich the context. It correlates these disparate inputs to generate formally structured Kaggle-compliant compliance reports classifying incidents into CRITICAL or HIGH severity.

### Robust Guardrails & Automated Evaluation Suite
System performance is rigorously audited against a Ground Truth (GT) golden dataset via an extensive automated test suite powered by `pytest` and integrated via `adk eval`. This evaluates PII leakage, RAG trajectory accuracy, and prompt adherence. It guarantees that the system correctly rejects impossible scenarios, flags missing annotations (`validate_labels`), catches LiDAR drops (`validate_telemetry`), and ensures zero information leakage before any report delivery is finalized.

Our platform stands as a testament to the power of multi-agent systems in heavily regulated, safety-critical business environments—bridging the gap between messy operational reality and precise, secure enterprise action.
