# CloudSage AI-Powered Multi-Cloud FinOps Copilot Architecture

## 1. Executive Summary

The **CloudSage AI FinOps Copilot** is an enterprise-grade conversational intelligence layer built directly on top of the CloudSage Multi-Cloud FinOps Platform. It enables CFOs, FinOps practitioners, engineering directors, and cloud architects to interact with their multi-cloud cost infrastructure (AWS, Microsoft Azure, Google Cloud Platform) using natural language.

Unlike generic chatbot implementations that execute dynamic, unpredictable SQL or hallucinate financial numbers, CloudSage Copilot employs a **strictly deterministic, evidence-grounded, advisory-only pipeline**. Every response is derived from verified database queries executed against canonical FOCUS 1.0 billing records, inventory models, waste detections, cost anomalies, and optimization recommendations.

---

## 2. Architectural Pillars

```
+-----------------------------------------------------------------------------------+
|                            User Prompt / Client API                               |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Step 1: Security & Advisory Guardrails                                            |
|   - Prompt Injection Defense                                                      |
|   - Mutation & Cloud Deletion Denial (Strict Advisory-Only Policy)                |
|   - Sensitive Credential Sanitization & Secret Scrubbing                          |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Step 2 & 3: Intent Classification & Entity Extraction                             |
|   - 15 Canonical FinOps Intent Categories                                         |
|   - Entity Extraction: Cloud Providers, Services, Resource IDs, Windows, Tags    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Step 4 & 5: Conversational Session & Context Memory                               |
|   - Multi-Turn Entity Carry-Over (Follow-up Context Resolution)                   |
|   - Session CRUD & Message Thread History                                         |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Step 6: Safe Analytical Query Planning                                            |
|   - Allowlisted Target Datasets (Billing, Inventory, Waste, Anomalies, Recs)      |
|   - Controlled Aggregations (SUM, COUNT, AVG, MIN, MAX)                           |
|   - Zero Raw SQL Execution Guarantee                                              |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Step 7: Cross-Stage Data Retrieval & Decimal Arithmetic                           |
|   - Parameterized SQLAlchemy ORM Queries                                          |
|   - Zero Float Rule: Strict Python Decimal & Numeric(18, 4)                       |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Step 8: Structured Evidence Citation Generation                                   |
|   - Canonical Table Linking (billing_records, cost_anomalies, waste_detections)   |
|   - Verifiable Confidence Scores and Exact Record References                      |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Step 9: Grounded Response Synthesis (LLM Provider / Deterministic Fallback)       |
|   - OpenAI / Azure OpenAI / vLLM / Local Model                                    |
|   - Offline Deterministic Fallback Synthesizer                                    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Step 10: Output Sanitization, Advisory Notice & Operational Telemetry Logging      |
|   - Mandatory Advisory Disclaimer Injection                                       |
|   - Operational Telemetry (Tokens, Duration ms, Status) in copilot_usage_logs     |
+-----------------------------------------------------------------------------------+
```

---

## 3. Component Breakdown

| Component | Module Path | Purpose |
| :--- | :--- | :--- |
| **Copilot Engine** | `backend/app/copilot/engine.py` | Central coordinator orchestrating the 8-step pipeline, chat turns, and explain endpoints. |
| **Intent Classifier** | `backend/app/copilot/intent.py` | Maps user questions to 15 canonical FinOps intents and extracts structured entities. |
| **Query Planner** | `backend/app/copilot/query_planner.py` | Generates allowlisted, parameterized execution plans; strictly prohibits arbitrary SQL. |
| **Data Retrieval Engine** | `backend/app/copilot/data_retrieval.py` | Safely queries stages 3–8 models; enforces Zero Float precision arithmetic. |
| **Citation Generator** | `backend/app/copilot/citations.py` | Converts database rows and metrics into structured, verifiable citations. |
| **Security Guardrails** | `backend/app/copilot/guardrails.py` | Blocks prompt injection, secret leaks, and enforces non-destructive advisory rules. |
| **LLM Provider Abstraction** | `backend/app/copilot/llm_provider.py` | Decouples LLM implementations; provides live OpenAI-compatible provider & deterministic fallback. |
| **Conversation Manager** | `backend/app/copilot/conversation.py` | Manages conversational persistence, multi-turn entity carry-over, and user feedback. |
| **Benchmark Suite** | `backend/app/copilot/benchmarks.py` | 30 deterministic FinOps benchmark queries with automated evaluation harness. |
| **REST API Router** | `backend/app/api/routes/copilot.py` | 10 FastAPI endpoints under `/api/v1/copilot`. |

---

## 4. Cross-Stage Data Grounding

CloudSage Copilot integrates seamlessly with every preceding stage of the CloudSage architecture:
- **Stage 3 & 4 (Billing)**: FOCUS 1.0 normalized billing line items, unblended cost, effective cost, pricing models, and SKU catalog mappings.
- **Stage 5 (Resource Inventory)**: Multi-cloud resources across AWS, Azure, and GCP, tags, operational states, and relationships.
- **Stage 6 (Waste Detection)**: Detected idle compute instances, unattached EBS/managed disks, orphaned snapshots, and unused IP addresses.
- **Stage 7 (Cost Anomaly Detection)**: Statistical spending deviations, service spikes, new spend events, and estimated excess expenditure.
- **Stage 8 (Advisory Recommendations)**: Prioritized optimization proposals, projected monthly/annual savings, risk scores, and human review states.

---

## 5. Security & Advisory-Only Guarantee

1. **Non-Destructive Principle**: CloudSage Copilot has zero write, mutate, or delete capabilities on hyperscaler infrastructure. Any user request asking the Copilot to terminate, resize, stop, or delete a cloud resource is intercepted by guardrails and declined with advisory guidance.
2. **Zero Dynamic SQL**: The Copilot never constructs or evaluates raw SQL strings generated by LLMs. All queries pass through the allowlisted `QueryPlan` schema and execute through parameterized SQLAlchemy ORM models.
3. **Tenant & Identity Isolation**: Conversations and messages are tagged with user and tenant IDs, preventing cross-tenant leakage.
4. **Secret Redaction**: Inbound and outbound streams are scanned against regex patterns for AWS keys, SSH private keys, and bearer tokens.
