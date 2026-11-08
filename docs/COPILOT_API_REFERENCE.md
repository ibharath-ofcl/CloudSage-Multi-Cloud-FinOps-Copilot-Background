# CloudSage AI FinOps Copilot REST API Reference

## Base URL
`/api/v1/copilot`

---

## Endpoint Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/chat` | Submit a natural language FinOps question and receive an evidence-grounded answer. |
| `GET` | `/conversations` | List conversation threads with pagination and optional user filter. |
| `GET` | `/conversations/{id}` | Retrieve complete conversation history and chronological message turns. |
| `DELETE` | `/conversations/{id}` | Delete a conversation thread and its associated messages. |
| `POST` | `/conversations/{id}/messages` | Append a new conversational turn to an existing thread. |
| `GET` | `/capabilities` | Retrieve supported intents, providers, aggregations, and active guardrails. |
| `GET` | `/health` | Health check endpoint reporting service, database, and provider statuses. |
| `GET` | `/usage` | Operational telemetry (token counts, latency, intent distribution). |
| `POST` | `/feedback` | Submit user rating (+1/-1) and commentary for an assistant response. |
| `POST` | `/explain` | Generate AI explainability analysis for an anomaly, waste item, or recommendation. |

---

## 1. POST `/chat`
Submits a user prompt to the Copilot. Creates a new conversation thread if `conversation_id` is omitted.

### Request Body
```json
{
  "query": "What is our total cloud spend this month across all providers?",
  "conversation_id": null,
  "user_id": "cfo_user_01",
  "model": "gpt-4o-mini"
}
```

### Response `200 OK`
```json
{
  "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "message_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "role": "ASSISTANT",
  "content": "### Executive Summary\nTotal recorded cloud expenditure is **$124,500.0000 USD** across **1,200** normalized billing records.\n\n### Detailed Breakdown\n- **AWS**: $65,200.0000 USD (52.4% of total spend)\n- **Azure**: $38,100.0000 USD (30.6% of total spend)\n- **GCP**: $21,200.0000 USD (17.0% of total spend)\n\n### Evidence & Citations\n- `billing_records`: FOCUS Normalized Billing: AWS Amazon EC2 — Value: **$150.2500 USD**\n\n### Advisory Next Steps\n- Review top spending dimensions for unexpected cost expansion.\n- Inspect active cost anomalies and waste detections to identify savings opportunities.\n\n*Advisory Notice: CloudSage recommendations are strictly advisory. Validate with system owners before implementing changes.*",
  "intent": "TOTAL_CLOUD_SPEND",
  "query_plan": {
    "intent": "TOTAL_CLOUD_SPEND",
    "target_dataset": "billing_records",
    "filters": {},
    "aggregations": ["SUM:unblended_cost", "COUNT:*"],
    "group_by": ["provider"],
    "time_range": {
      "start_time": "2026-10-08T12:00:00+00:00",
      "end_time": "2026-11-07T12:00:00+00:00"
    }
  },
  "evidence_citations": [
    {
      "source_table": "billing_records",
      "record_id": "4b68e912-32b1-4190-8b1e-2cb4f5a91012",
      "description": "FOCUS Normalized Billing: AWS Amazon EC2",
      "metric_value": "$150.2500 USD",
      "confidence": 1.0
    }
  ],
  "tokens_used": 285,
  "execution_duration_ms": 142,
  "model_name": "gpt-4o-mini",
  "provider": "openai",
  "advisory_disclaimer": "CloudSage recommendations are strictly advisory. No automatic cloud resource modification or deletion is performed.",
  "created_at": "2026-11-07T18:40:00Z"
}
```

---

## 2. GET `/conversations`
Lists conversation threads.

### Query Parameters
- `user_id` (optional, string): Filter by user identity.
- `limit` (optional, integer, default: 20, min: 1, max: 100).
- `offset` (optional, integer, default: 0).

### Response `200 OK`
```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "user_id": "cfo_user_01",
    "title": "What is our total cloud spend this month across all providers?",
    "created_at": "2026-11-07T18:35:00Z",
    "updated_at": "2026-11-07T18:40:00Z",
    "message_count": 2
  }
]
```

---

## 3. GET `/conversations/{id}`
Retrieves complete conversation thread with chronological messages.

### Response `200 OK`
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "user_id": "cfo_user_01",
  "title": "What is our total cloud spend this month across all providers?",
  "created_at": "2026-11-07T18:35:00Z",
  "updated_at": "2026-11-07T18:40:00Z",
  "messages": [
    {
      "id": "1fa85f64-5717-4562-b3fc-2c963f66afa1",
      "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "role": "USER",
      "content": "What is our total cloud spend this month across all providers?",
      "intent": "TOTAL_CLOUD_SPEND",
      "query_plan": null,
      "evidence_citations": [],
      "tokens_used": 0,
      "execution_duration_ms": 0,
      "model_name": null,
      "provider": null,
      "created_at": "2026-11-07T18:35:00Z"
    },
    {
      "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "role": "ASSISTANT",
      "content": "### Executive Summary\nTotal recorded cloud expenditure is...",
      "intent": "TOTAL_CLOUD_SPEND",
      "query_plan": { ... },
      "evidence_citations": [ ... ],
      "tokens_used": 285,
      "execution_duration_ms": 142,
      "model_name": "gpt-4o-mini",
      "provider": "openai",
      "created_at": "2026-11-07T18:40:00Z"
    }
  ]
}
```

---

## 4. DELETE `/conversations/{id}`
Deletes a conversation thread and cascades deletion of its messages.

### Response `200 OK`
```json
{
  "status": "success",
  "message": "Conversation '3fa85f64-5717-4562-b3fc-2c963f66afa6' deleted."
}
```

---

## 5. POST `/conversations/{id}/messages`
Appends a new turn to an existing conversation thread. Accepts identical payload structure to `/chat`.

---

## 6. GET `/capabilities`
Returns operational features, supported intents, and guardrail settings.

### Response `200 OK`
```json
{
  "supported_intents": [
    "TOTAL_CLOUD_SPEND",
    "PROVIDER_COST_COMPARISON",
    "SERVICE_COST_BREAKDOWN",
    "RESOURCE_COST_ANALYSIS",
    "COST_TREND_ANALYSIS",
    "COST_ANOMALY_EXPLANATION",
    "WASTE_DETECTION_ANALYSIS",
    "OPTIMIZATION_RECOMMENDATIONS",
    "SAVINGS_OPPORTUNITY",
    "RESOURCE_UTILIZATION",
    "OWNER_COST_ANALYSIS",
    "COST_CENTER_ANALYSIS",
    "BILLING_DATA_QUALITY",
    "GENERAL_FINOPS_QUESTION",
    "UNSUPPORTED_OR_AMBIGUOUS_QUERY"
  ],
  "supported_providers": ["AWS", "AZURE", "GCP"],
  "supported_aggregations": ["SUM", "COUNT", "AVG", "MIN", "MAX"],
  "guardrails_enabled": true,
  "advisory_mode": true,
  "active_model": "gpt-4o-mini",
  "active_provider": "deterministic-fallback"
}
```

---

## 7. GET `/health`
Reports health status of the Copilot service and underlying database.

### Response `200 OK`
```json
{
  "status": "healthy",
  "database_connected": true,
  "provider_status": "active_deterministic_fallback",
  "active_model": "gpt-4o-mini",
  "timestamp": "2026-11-07T18:42:00Z"
}
```

---

## 8. GET `/usage`
Telemetry audit showing total invocations, tokens consumed, average latency, and distribution.

### Response `200 OK`
```json
{
  "total_queries": 42,
  "total_tokens": 12450,
  "average_latency_ms": 118.4,
  "provider_breakdown": {
    "deterministic-fallback": 40,
    "internal": 2
  },
  "intent_breakdown": {
    "TOTAL_CLOUD_SPEND": 14,
    "PROVIDER_COST_COMPARISON": 8,
    "OPTIMIZATION_RECOMMENDATIONS": 10,
    "GUARDRAIL_VIOLATION": 2,
    "WASTE_DETECTION_ANALYSIS": 8
  }
}
```

---

## 9. POST `/feedback`
Submits user rating and commentary for an assistant response.

### Request Body
```json
{
  "message_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "rating": 1,
  "feedback_text": "Accurate figures and verifiable citations.",
  "user_id": "cfo_user_01"
}
```

### Response `201 Created`
```json
{
  "id": "e4b85f64-5717-4562-b3fc-2c963f66af77",
  "message_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "rating": 1,
  "feedback_text": "Accurate figures and verifiable citations.",
  "created_at": "2026-11-07T18:42:10Z"
}
```

---

## 10. POST `/explain`
Generates deep FinOps technical and business explainability for a finding.

### Request Body
```json
{
  "target_type": "anomaly",
  "target_id": "92da1048-4390-4822-ba4a-efc98421b011",
  "user_id": "finops_analyst_01"
}
```

### Response `200 OK`
```json
{
  "target_type": "anomaly",
  "target_id": "92da1048-4390-4822-ba4a-efc98421b011",
  "title": "Cost Anomaly on AWS Amazon RDS (SERVICE_SPIKE)",
  "explanation": "### Root Cause Analysis\nA **HIGH** cost anomaly was detected on **AWS Amazon RDS** under category **SERVICE_SPIKE**. Estimated unexpected expenditure is **$450.7500 USD**.\nThe spending deviated significantly from baseline expectations.",
  "evidence_citations": [
    {
      "source_table": "cost_anomalies",
      "record_id": "92da1048-4390-4822-ba4a-efc98421b011",
      "description": "Stage 7 Anomaly: AWS Amazon RDS (SERVICE_SPIKE)",
      "metric_value": "$450.7500 excess",
      "confidence": 0.98
    }
  ],
  "financial_impact": {
    "estimated_excess_cost": "450.7500",
    "currency": "USD",
    "severity": "HIGH",
    "status": "OPEN"
  },
  "advisory_recommendation": "Verify whether the spending jump on Amazon RDS correlates with a scheduled deployment or campaign. If unintended, inspect provisioned capacity and set up budget threshold alerts.",
  "advisory_disclaimer": "CloudSage recommendations are strictly advisory. No automatic cloud resource modification or deletion is performed."
}
```

