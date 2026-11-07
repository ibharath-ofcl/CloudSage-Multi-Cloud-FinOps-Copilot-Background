"""
CloudSage GCP Field & Service Category Mappings.
"""

from typing import Dict
from backend.app.core.enums import PricingModel, ServiceCategory

GCP_SERVICE_CATEGORY_MAP: Dict[str, ServiceCategory] = {
    # Compute
    "compute engine": ServiceCategory.COMPUTE,
    "cloud functions": ServiceCategory.COMPUTE,
    "cloud run": ServiceCategory.COMPUTE,
    "google kubernetes engine": ServiceCategory.COMPUTE,
    "kubernetes engine": ServiceCategory.COMPUTE,
    "app engine": ServiceCategory.COMPUTE,

    # Storage
    "cloud storage": ServiceCategory.STORAGE,
    "persistent disk": ServiceCategory.STORAGE,
    "filestore": ServiceCategory.STORAGE,
    "backup and dr": ServiceCategory.STORAGE,

    # Database
    "cloud sql": ServiceCategory.DATABASE,
    "cloud spanner": ServiceCategory.DATABASE,
    "cloud bigtable": ServiceCategory.DATABASE,
    "memorystore": ServiceCategory.DATABASE,
    "firestore": ServiceCategory.DATABASE,
    "datastore": ServiceCategory.DATABASE,

    # Networking
    "cloud load balancing": ServiceCategory.NETWORKING,
    "cloud nat": ServiceCategory.NETWORKING,
    "cloud dns": ServiceCategory.NETWORKING,
    "cloud vpn": ServiceCategory.NETWORKING,
    "cloud interconnect": ServiceCategory.NETWORKING,
    "cloud cdn": ServiceCategory.NETWORKING,
    "virtual private cloud": ServiceCategory.NETWORKING,
    "network": ServiceCategory.NETWORKING,

    # AI & ML
    "vertex ai": ServiceCategory.AI_ML,
    "automl": ServiceCategory.AI_ML,
    "natural language api": ServiceCategory.AI_ML,
    "cloud vision": ServiceCategory.AI_ML,
    "speech-to-text": ServiceCategory.AI_ML,

    # Analytics
    "bigquery": ServiceCategory.ANALYTICS,
    "cloud dataflow": ServiceCategory.ANALYTICS,
    "dataproc": ServiceCategory.ANALYTICS,
    "cloud pub/sub": ServiceCategory.ANALYTICS,
    "looker": ServiceCategory.ANALYTICS,

    # Management & Security
    "cloud monitoring": ServiceCategory.MANAGEMENT,
    "cloud logging": ServiceCategory.MANAGEMENT,
    "cloud trace": ServiceCategory.MANAGEMENT,
    "cloud key management service": ServiceCategory.SECURITY,
    "cloud kms": ServiceCategory.SECURITY,
    "cloud armor": ServiceCategory.SECURITY,
    "security command center": ServiceCategory.SECURITY,
}
