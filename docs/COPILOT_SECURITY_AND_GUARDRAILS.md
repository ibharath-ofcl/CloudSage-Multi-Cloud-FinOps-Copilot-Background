# CloudSage Copilot Security Architecture & Policy Guardrails

## 1. Security Threat Model for Enterprise FinOps

An enterprise AI FinOps Copilot interacts with sensitive multi-cloud infrastructure and financial data. The threat model addresses four distinct vulnerability classes:
1. **Adversarial Prompt Injection & Jailbreaking**: Attempts to override system instructions, extract proprietary prompts, or trick the model into roleplay.
2. **Unauthorized Mutation & Resource Deletion**: Attempts to command the Copilot to execute mutating, destructive cloud actions (e.g. "delete instance", "shut down cluster").
3. **Data Exfiltration & Credential Leakage**: Leakage of cloud credentials (AWS Access Keys, SSH keys, bearer tokens) through prompts or generated output.
4. **SQL Injection & Unauthorized Schema Probing**: Execution of arbitrary SQL statements or exfiltration of database metadata.

---

## 2. Multi-Layer Guardrail Architecture

```
User Prompt
    │
    ▼
[ Guardrail Layer 1: Prompt Injection Detection ]
    ├── System prompt extraction patterns
    ├── Instruction override patterns ("ignore previous instructions")
    └── Roleplay / Jailbreak patterns ("DAN mode", "god mode")
    │
    ▼
[ Guardrail Layer 2: Advisory-Only Policy Enforcement ]
    ├── Mutating verb detection (delete, terminate, stop, reboot, resize)
    ├── Target cloud resource detection (instance, VM, database, disk)
    └── Immediate rejection with Advisory Notice
    │
    ▼
[ Guardrail Layer 3: Sensitive Credential Detection ]
    ├── AWS Access Key ID regex (AKIA...)
    ├── GitHub Personal Access Token regex (ghp_...)
    └── Private RSA / OpenSSH key blocks
    │
    ▼
[ Execution Pipeline: Allowlisted Query Planning ]
    ├── Zero raw SQL execution
    └── Strict allowlists on datasets, aggregations, and dimensions
    │
    ▼
[ Output Sanitization Layer ]
    ├── Credential masking ([REDACTED_SECRET])
    └── Mandatory Advisory Disclaimer Injection
```

---

## 3. The Advisory-Only Policy (Strict Non-Destructive Invariant)

CloudSage is an **advisory-only** FinOps platform. Recommendations must always be reviewed, endorsed, and implemented by authorized human engineers.

### Enforcement Rule:
Whenever a user query attempts to trigger infrastructure deletion, termination, stopping, or modification, the Copilot immediately refuses:

> *"CloudSage operates strictly as an advisory FinOps copilot. Direct infrastructure modifications, automatic resource termination, or deletion actions are strictly prohibited. Please review and execute recommended actions through your cloud management console or IaC pipelines."*

Every response providing savings or optimization advice is appended with the mandatory advisory disclaimer:
> *\*Advisory Notice: CloudSage recommendations are strictly advisory. Validate with system owners before implementing changes.\**

---

## 4. Prompt Injection Defense Rules

The `CopilotGuardrails` class (`backend/app/copilot/guardrails.py`) monitors inbound user queries against calibrated regex heuristics targeting prompt injection attacks:
- `ignore (all )?(previous|prior|above) (instructions|directions)`
- `system prompt (reveal|leak|show|print|dump)`
- `what are your (original|system|core) instructions`
- `act as (dan|an unfiltered|root|admin)`
- `jailbreak`
- `bypass safety`
- `you are now in god mode`

Violations return an immediate safe refusal with intent `GUARDRAIL_VIOLATION` and are logged to `copilot_usage_logs` with status `blocked_PROMPT_INJECTION_DETECTED`.

---

## 5. Sensitive Token Sanitization

Inbound queries and outbound generated texts are scrubbed against credential patterns:
- **AWS Keys**: `AKIA[0-9A-Z]{16}`
- **GitHub Tokens**: `ghp_[0-9a-zA-Z]{36}`
- **Private Keys**: `-----BEGIN (RSA|OPENSSH|DSA|EC)? PRIVATE KEY-----`
- **JWT Tokens**: `eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+`

If detected in the input, the query is blocked (`SENSITIVE_DATA_DETECTED`). If present in output, secrets are replaced with `[REDACTED_SECRET]`.

