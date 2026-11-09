# CloudSage Tamper-Evident Audit Logging & Governance

## 1. Overview
CloudSage implements a cryptographically chained, tamper-evident audit ledger that ensures non-repudiation for all sensitive operations, recommendations, alerts, and user modifications. Any unauthorized direct modification or deletion of database records is mathematically detectable.

---

## 2. SHA-256 Hash Chaining Architecture

```
Genesis Record (00000000...)
       │
       ▼
┌─────────────────────────────────┐
│ Audit Record #1                 │
│ previous_hash: 000000000000...  │
│ payload:       USER_CREATE      │
│ record_hash:   SHA256(canonical)├──┐
└─────────────────────────────────┘  │
                                     ▼
┌─────────────────────────────────┐  │
│ Audit Record #2                 │  │
│ previous_hash: [Hash of Rec #1] <──┘
│ payload:       APPROVE_SAVINGS  │
│ record_hash:   SHA256(canonical)├──┐
└─────────────────────────────────┘  │
                                     ▼
┌─────────────────────────────────┐  │
│ Audit Record #3                 │  │
│ previous_hash: [Hash of Rec #2] <──┘
│ payload:       UPDATE_POLICY    │
│ record_hash:   SHA256(canonical)│
└─────────────────────────────────┘
```

### Canonical String Representation
To guarantee deterministic hashing across database drivers and platforms:
```python
canonical_representation = (
    f"{previous_hash}|{normalized_timestamp}|{user_email}|"
    f"{action_type}|{resource_type}|{resource_id}|{status}|"
    f"{json_before_state}|{json_after_state}"
)
record_hash = hashlib.sha256(canonical_representation.encode("utf-8")).hexdigest()
```

---

## 3. Secret Redaction Pipeline

Before any state payload (`before_state` or `after_state`) is hashed or persisted to PostgreSQL/SQLite, it passes through `redact_secrets()`:
- Recursively inspects all dictionary keys and nested lists.
- Any key matching sensitive terms (`password`, `hashed_password`, `token`, `secret`, `api_key`, `authorization`, `cookie`) has its value scrubbed to `"[REDACTED]"`.
- Plaintext secrets NEVER touch the audit log table or disk.

---

## 4. Hash Chain Verification Engine

CloudSage provides an on-demand verification endpoint (`POST /api/v1/admin/security/audit-integrity/verify`) and automated background checks:
1. Iterates through records in ascending chronological sequence.
2. Verifies that `rec[i].previous_hash == rec[i-1].record_hash`.
3. Recomputes `SHA256(canonical_representation)` and verifies it matches `rec[i].record_hash`.
4. If an attacker modifies an `after_state` or deletes an intermediate row, the computed hash mismatches, and `verify_chain()` reports:
   `"Chain broken at record #{id}: expected prev {expected_prev}, found {actual}"`
   or
   `"Hash mismatch at record #{id}: computed {computed}, found {stored}"`

---

## 5. Regulatory Compliance Checkpoints

For SOC 2 Type II, ISO 27001, and external financial audits:
- Administrators or automated cron jobs create immutable cryptographic checkpoints (`AuditIntegrityCheckpoint`).
- Each checkpoint records:
  - `checkpoint_hash`: The cumulative SHA-256 seal of the current ledger state.
  - `record_count`: Number of verified records sealed.
  - `verified_by`: Identity of the auditor or service account.
  - `verified_at`: UTC timestamp of the seal.
- Checkpoints provide frozen snapshots for external regulators proving no retrospective tampering has occurred.
