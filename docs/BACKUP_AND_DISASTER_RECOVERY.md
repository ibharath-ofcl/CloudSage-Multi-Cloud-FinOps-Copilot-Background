# CloudSage Database Backup & Disaster Recovery (DR)

## 1. Disaster Recovery Objectives

- **Recovery Point Objective (RPO):** $< 1\text{ hour}$ (Automated continuous snapshots & WAL archiving).
- **Recovery Time Objective (RTO):** $< 15\text{ minutes}$ (Fast point-in-time restore procedure).
- **Integrity Guarantee:** Cryptographic SHA256 validation of every generated archive.

---

## 2. Backup Utility (`backend/scripts/backup_db.sh`)

### Operational Workflow:
1. Connects to PostgreSQL using configured environment parameters.
2. Invokes `pg_dump` with gzip compression and `--clean --if-exists` flags.
3. Generates a timestamped archive: `cloudsage_backup_YYYYMMDD_HHMMSS.sql.gz`.
4. Calculates SHA256 checksum and saves to `.sql.gz.sha256`.
5. Prunes backups exceeding the retention threshold (default 30 days).

### Manual Invocation:
```bash
# Execute manual backup locally or inside container
bash backend/scripts/backup_db.sh
```

---

## 3. Safe Database Restoration (`backend/scripts/restore_db.sh`)

### Safety Guards:
1. **Accidental Overwrite Protection:** Restorations will immediately abort with exit code `2` unless explicitly confirmed by passing `--force` or setting `CONFIRM_RESTORE=true`.
2. **Cryptographic Checksum Verification:** Restorations will immediately abort with exit code `3` if the archive's computed SHA256 checksum does not match its companion `.sha256` manifest.
3. **Transactional Safety:** Restores within a single transaction where supported, ensuring no partial or corrupted state remains on failure.

### Restore Execution:
```bash
# Execute safe database restoration
bash backend/scripts/restore_db.sh /backups/cloudsage_backup_20261109_140000.sql.gz --force
```

---

## 4. Disaster Recovery Scenarios & Playbooks

### Scenario A: Corruption Prior to Database Migration
1. Pre-deployment backup exists in `/backups` as triggered by CD Step 3A.
2. Terminate application ingress: `docker compose -f docker-compose.prod.yml stop ingress backend`.
3. Restore pre-migration backup snapshot via `restore_db.sh`.
4. Restart backend and ingress containers.

### Scenario B: Complete Hardware / Region Failure
1. Provision target infrastructure via Terraform / Kubernetes.
2. Retrieve the latest encrypted backup archive and `.sha256` manifest from cross-region cold storage (e.g. AWS S3 Glacier, GCP Coldline).
3. Initialize PostgreSQL container with persistent volume.
4. Execute `restore_db.sh <backup_file> --force`.
5. Point DNS / Ingress to the restored regional cluster.

