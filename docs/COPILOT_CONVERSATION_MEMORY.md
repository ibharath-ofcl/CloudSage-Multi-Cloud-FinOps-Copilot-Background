# CloudSage Copilot Conversational Memory & Context Resolution

## 1. Overview

Enterprise cloud financial inquiries are rarely single-turn questions. A user typically begins with an exploratory question (*"What did we spend on cloud this month?"*), followed by drills-downs (*"And how much of that was AWS?"*), followed by service inspections (*"What about EC2?"*).

The CloudSage Copilot manages persistent multi-turn conversational memory, enabling seamless contextual continuity while maintaining strict user and tenant isolation.

---

## 2. Conversational Data Models

Conversational memory is persisted across four dedicated PostgreSQL tables:

```
+-------------------------------------------------------------+
|                     copilot_conversations                   |
|-------------------------------------------------------------|
| id (UUID, PK)                                               |
| user_id (VARCHAR(100), INDEX)                               |
| title (VARCHAR(255))                                        |
| created_at (TIMESTAMPTZ)                                    |
| updated_at (TIMESTAMPTZ, INDEX)                             |
+-------------------------------------------------------------+
                               |
                               | 1:N (CASCADE DELETE)
                               v
+-------------------------------------------------------------+
|                      copilot_messages                       |
|-------------------------------------------------------------|
| id (UUID, PK)                                               |
| conversation_id (UUID, FK, INDEX)                           |
| role (VARCHAR(32)) - USER, ASSISTANT, SYSTEM                |
| content (TEXT)                                              |
| intent (VARCHAR(64), INDEX)                                 |
| query_plan (JSONB)                                          |
| evidence_citations (JSONB)                                  |
| tokens_used (INTEGER)                                       |
| execution_duration_ms (INTEGER)                             |
| model_name (VARCHAR(100))                                   |
| provider (VARCHAR(50))                                      |
| raw_metadata (JSONB)                                        |
| created_at (TIMESTAMPTZ, INDEX)                             |
+-------------------------------------------------------------+
          |                                        |
          | 1:1                                    | Audit Stream
          v                                        v
+----------------------------------+    +----------------------------------+
|         copilot_feedback         |    |        copilot_usage_logs        |
|----------------------------------|    |----------------------------------|
| id (UUID, PK)                    |    | id (UUID, PK)                    |
| message_id (UUID, FK, UNIQUE)    |    | user_id (VARCHAR(100), INDEX)    |
| user_id (VARCHAR(100))           |    | conversation_id (VARCHAR(100))   |
| rating (INTEGER) - (+1, -1)      |    | model_name (VARCHAR(100))        |
| feedback_text (TEXT)             |    | provider (VARCHAR(50))           |
| created_at (TIMESTAMPTZ)         |    | prompt_tokens (INTEGER)          |
+----------------------------------+    | completion_tokens (INTEGER)      |
                                        | total_tokens (INTEGER)           |
                                        | execution_duration_ms (INTEGER)  |
                                        | status (VARCHAR(50))             |
                                        | created_at (TIMESTAMPTZ, INDEX)  |
                                        +----------------------------------+
```

---

## 3. Multi-Turn Entity Carry-Over (Context Resolution)

When a follow-up query omits specific cloud dimensions, `ConversationManager.resolve_follow_up_context` analyzes the chronological message thread to carry forward relevant filters:

### Example Scenario:
- **Turn 1 (User)**: *"How much did we spend on AWS EC2 last month?"*
  - Extracted Entities: `providers = ["AWS"]`, `services = ["Amazon EC2"]`
  - Assistant answers with AWS EC2 figures and saves `query_plan` with those filters.
- **Turn 2 (User)**: *"And how does that compare to last week?"*
  - Extracted Entities: `providers = []`, `services = []`, `time_window = "last_7_days"`
  - **Context Resolution**: The engine inspects preceding turns, detects that `providers` and `services` were omitted, and injects `providers = ["AWS"]` and `services = ["Amazon EC2"]`.
  - The Query Planner constructs an accurate, scoped query for AWS EC2 without prompting the user to repeat themselves.

---

## 4. Title Auto-Generation

New conversation threads are created with a placeholder title (`"FinOps Analysis"`). Upon processing the first user message turn, the title is automatically updated to the first 60 characters of the user prompt (e.g., *"What is our total spend on Google Cloud?"*), giving users meaningful conversational history in the UI.

---

## 5. Human-in-the-Loop Feedback & Audit Telemetry

- **Rating System**: Users can submit binary feedback (`+1` for helpful, `-1` for unhelpful/incorrect) alongside qualitative commentary via `POST /api/v1/copilot/feedback`.
- **Telemetry Audit**: Every chat turn, whether completed successfully or blocked by safety guardrails, is recorded in `copilot_usage_logs` with prompt tokens, completion tokens, roundtrip latency, and status.
