# Multi-Cloud Resource Topology & Relationships

## 1. Overview

Cloud resources rarely exist in isolation. Modern enterprise infrastructure operates as a directed acyclic graph (DAG): virtual machines attach to network interfaces and block volumes, while backup snapshots descend from volumes.

The `resource_relationships` table enables CloudSage to model multi-cloud topology graphs. This structural awareness is essential for Stage 6: **Cloud Waste Detection** (e.g. detecting unattached volumes, abandoned snapshots, and orphaned IPs).

---

## 2. Supported Relationship Types

| Relationship Type | Source Entity | Target Entity | Use Case |
|:---|:---|:---|:---|
| `ATTACHED_TO` | Compute Instance (EC2, VM, GCE) | Block Volume (EBS, Managed Disk, PD) | Detect unattached / orphaned disks. |
| `ATTACHED_TO` | Compute Instance | Virtual Network (VNET, VPC, Subnet) | Map network connectivity & security groups. |
| `SNAPSHOT_OF` | Backup Snapshot | Block Volume | Identify abandoned snapshots whose parent volume was deleted. |
| `MEMBER_OF` | Instance / Pod | Cluster / Auto Scaling Group | Understand cluster membership & fleet rightsizing. |
| `ASSOCIATED_WITH` | Elastic IP / Public IP | Compute Instance or NAT Gateway | Detect idle, unassociated public IPv4 addresses. |

---

## 3. Directional Schema & Deduplication

```sql
CREATE TABLE resource_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_resource_id VARCHAR(512) NOT NULL REFERENCES cloud_resources(resource_id) ON DELETE CASCADE,
    target_resource_id VARCHAR(512) NOT NULL,
    relationship_type VARCHAR(64) NOT NULL,
    provider VARCHAR(16) NOT NULL,
    discovery_source VARCHAR(32) NOT NULL DEFAULT 'INVENTORY_DISCOVERY',
    confidence NUMERIC(5, 4) NOT NULL DEFAULT 1.0000,
    first_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    relationship_metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT uq_resource_relationships UNIQUE (source_resource_id, target_resource_id, relationship_type)
);
```

### Guarantees
1. **Deduplication**: The composite unique constraint `uq_resource_relationships` prevents duplicate edges when reconciling snapshots repeatedly.
2. **Referential Integrity**: Source resource foreign key cascades if a source resource record is explicitly archived.
3. **Target Loose Coupling**: `target_resource_id` allows pointing to external or deleted resources (e.g. snapshots whose source volume has already been destroyed in the cloud).
