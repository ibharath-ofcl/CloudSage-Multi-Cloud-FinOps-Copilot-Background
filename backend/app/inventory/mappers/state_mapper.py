"""
CloudSage State Mapper.
Maps provider-specific operational and lifecycle states to canonical CloudSage resource states:
'active', 'stopped', 'terminated', 'deleted', 'unknown', 'pending'.
"""

from typing import Dict


class StateMapper:
    """Normalizes hyperscaler resource lifecycle states."""

    # AWS state mappings
    AWS_STATE_MAP: Dict[str, str] = {
        # EC2
        "running": "active",
        "stopped": "stopped",
        "stopping": "pending",
        "shutting-down": "pending",
        "terminated": "terminated",
        "pending": "pending",
        # EBS
        "in-use": "active",
        "available": "available",  # unattached disk
        "creating": "pending",
        "deleting": "deleted",
        "deleted": "deleted",
        "error": "unknown",
        # RDS
        "available": "active",
        "backing-up": "active",
        "modifying": "active",
        "starting": "pending",
        "stopped": "stopped",
        "stopping": "pending",
        "failed": "unknown",
        # S3 / Lambda / Snapshots
        "completed": "active",
        "active": "active",
    }

    # Azure state mappings
    AZURE_STATE_MAP: Dict[str, str] = {
        # VM power states
        "vm running": "active",
        "running": "active",
        "vm stopped": "stopped",
        "stopped": "stopped",
        "vm deallocated": "stopped",
        "deallocated": "stopped",
        "vm starting": "pending",
        "starting": "pending",
        "vm stopping": "pending",
        "vm deallocating": "pending",
        "vm deleting": "deleted",
        # Disks
        "attached": "active",
        "unattached": "available",  # unattached disk
        "reserved": "active",
        # General
        "succeeded": "active",
        "ready": "active",
        "failed": "unknown",
    }

    # GCP state mappings
    GCP_STATE_MAP: Dict[str, str] = {
        # GCE instances
        "running": "active",
        "stopped": "stopped",
        "terminated": "stopped",
        "suspended": "stopped",
        "staging": "pending",
        "provisioning": "pending",
        "stopping": "pending",
        "repairing": "pending",
        # Disks
        "ready": "available",
        "attached": "active",
        "creating": "pending",
        "deleting": "deleted",
        "failed": "unknown",
        # Cloud SQL / Storage
        "runnable": "active",
        "suspended": "stopped",
    }

    @classmethod
    def normalize_state(cls, provider: str, raw_state: str) -> str:
        """Translates raw provider state string to standard canonical state."""
        if not raw_state:
            return "unknown"

        cleaned = str(raw_state).strip().lower()
        prov = provider.upper().strip()

        if prov == "AWS":
            return cls.AWS_STATE_MAP.get(cleaned, "unknown")
        elif prov == "AZURE":
            return cls.AZURE_STATE_MAP.get(cleaned, "unknown")
        elif prov == "GCP":
            return cls.GCP_STATE_MAP.get(cleaned, "unknown")

        return "unknown"
