# Cloud Provider Inventory Adapters

## 1. Adapter Contract (`BaseInventoryAdapter`)

All cloud provider inventory adapters inherit from `BaseInventoryAdapter` and implement two standardized ingestion modes:

```python
class BaseInventoryAdapter(ABC):
    @property
    @abstractmethod
    def provider(self) -> CloudProvider: ...

    @abstractmethod
    def parse_export(self, stream_or_path: Any, source_identifier: str) -> AdapterDiscoveryResult:
        """Mode A: Offline file-based parsing."""
        ...

    @abstractmethod
    def discover_live(self, regions: Optional[List[str]], resource_types: Optional[List[str]]) -> AdapterDiscoveryResult:
        """Mode B: Live read-only control plane probing."""
        ...
```

---

## 2. AWS Inventory Adapter (`AWSInventoryAdapter`)

### Supported Resource Types
- **Compute**: Amazon EC2 (`ec2:instance`), AWS Lambda (`lambda:function`)
- **Storage**: Amazon EBS Volumes (`ec2:volume`), Amazon S3 Buckets (`s3:bucket`)
- **Database**: Amazon RDS Instances (`rds:db`, `rds:cluster`)
- **Backup / Protection**: Amazon EBS Snapshots (`ec2:snapshot`)

### Extracted Relationships
- `EC2 Instance --[ATTACHED_TO]--> EBS Volume` (via `attached_volume_ids` / `block_device_mappings`)
- `EBS Snapshot --[SNAPSHOT_OF]--> EBS Volume` (via `source_volume_id`)

### Live Discovery Credentials
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`
- Strict IAM Policy Requirement: `arn:aws:iam::aws:policy/ReadOnlyAccess`

---

## 3. Azure Inventory Adapter (`AzureInventoryAdapter`)

### Supported Resource Types
- **Compute**: Azure Virtual Machines (`Microsoft.Compute/virtualMachines`)
- **Storage**: Azure Managed Disks (`Microsoft.Compute/disks`), Azure Storage Accounts (`Microsoft.Storage/storageAccounts`)
- **Database**: Azure SQL Databases (`Microsoft.Sql/servers/databases`)
- **Networking**: Azure Virtual Networks (`Microsoft.Network/virtualNetworks`)
- **Snapshots**: Azure Managed Snapshots (`Microsoft.Compute/snapshots`)

### Extracted Relationships
- `Virtual Machine --[ATTACHED_TO]--> Managed Disk` (via `storageProfile.osDisk`, `storageProfile.dataDisks`)
- `Virtual Machine --[ATTACHED_TO]--> Virtual Network` (via `networkProfile.networkInterfaces`)
- `Snapshot --[SNAPSHOT_OF]--> Managed Disk` (via `creationData.sourceResourceId`)

### Live Discovery Credentials
- `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
- Strict RBAC Role Requirement: `Reader` role on subscriptions or management groups.

---

## 4. GCP Inventory Adapter (`GCPInventoryAdapter`)

### Supported Resource Types
- **Compute**: Google Compute Engine (`compute.googleapis.com/Instance`)
- **Storage**: GCE Persistent Disks (`compute.googleapis.com/Disk`), Cloud Storage Buckets (`storage.googleapis.com/Bucket`)
- **Database**: Cloud SQL Instances (`sqladmin.googleapis.com/Instance`)
- **Networking**: VPC Networks (`compute.googleapis.com/Network`)
- **Snapshots**: Compute Engine Snapshots (`compute.googleapis.com/Snapshot`)

### Extracted Relationships
- `GCE Instance --[ATTACHED_TO]--> Persistent Disk` (via `disks.source`)
- `GCE Instance --[ATTACHED_TO]--> VPC Network` (via `networkInterfaces.network`)
- `Snapshot --[SNAPSHOT_OF]--> Persistent Disk` (via `sourceDisk`)

### Live Discovery Credentials
- `GOOGLE_APPLICATION_CREDENTIALS` (Service Account JSON) or `GCP_PROJECT_ID` with ADC.
- Strict IAM Role Requirement: `roles/cloudasset.viewer` or `roles/viewer`.
