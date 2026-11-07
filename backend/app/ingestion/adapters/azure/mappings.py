"""
CloudSage Azure Field & Service Category Mappings.
"""

from typing import Dict
from backend.app.core.enums import PricingModel, ServiceCategory

AZURE_METER_CATEGORY_MAP: Dict[str, ServiceCategory] = {
    # Compute
    "virtual machines": ServiceCategory.COMPUTE,
    "azure functions": ServiceCategory.COMPUTE,
    "container instances": ServiceCategory.COMPUTE,
    "azure kubernetes service": ServiceCategory.COMPUTE,
    "app service": ServiceCategory.COMPUTE,
    "cloud services": ServiceCategory.COMPUTE,
    "batch": ServiceCategory.COMPUTE,

    # Storage
    "storage": ServiceCategory.STORAGE,
    "managed disks": ServiceCategory.STORAGE,
    "backup": ServiceCategory.STORAGE,
    "azure data lake storage": ServiceCategory.STORAGE,

    # Database
    "sql database": ServiceCategory.DATABASE,
    "azure cosmos db": ServiceCategory.DATABASE,
    "azure database for postgresql": ServiceCategory.DATABASE,
    "azure database for mysql": ServiceCategory.DATABASE,
    "azure cache for redis": ServiceCategory.DATABASE,
    "synapse analytics": ServiceCategory.DATABASE,

    # Networking
    "networking": ServiceCategory.NETWORKING,
    "bandwidth": ServiceCategory.NETWORKING,
    "virtual network": ServiceCategory.NETWORKING,
    "vpn gateway": ServiceCategory.NETWORKING,
    "application gateway": ServiceCategory.NETWORKING,
    "azure firewall": ServiceCategory.NETWORKING,
    "load balancer": ServiceCategory.NETWORKING,
    "dns": ServiceCategory.NETWORKING,

    # AI & ML
    "cognitive services": ServiceCategory.AI_ML,
    "azure openapi": ServiceCategory.AI_ML,
    "machine learning": ServiceCategory.AI_ML,
    "bot service": ServiceCategory.AI_ML,

    # Analytics
    "azure databricks": ServiceCategory.ANALYTICS,
    "event hubs": ServiceCategory.ANALYTICS,
    "stream analytics": ServiceCategory.ANALYTICS,
    "data factory": ServiceCategory.ANALYTICS,

    # Management
    "azure monitor": ServiceCategory.MANAGEMENT,
    "log analytics": ServiceCategory.MANAGEMENT,
    "automation": ServiceCategory.MANAGEMENT,
    "security center": ServiceCategory.SECURITY,
    "key vault": ServiceCategory.SECURITY,
}

AZURE_PRICING_MODEL_MAP: Dict[str, PricingModel] = {
    "ondemand": PricingModel.ON_DEMAND,
    "payg": PricingModel.ON_DEMAND,
    "reservation": PricingModel.RESERVED,
    "reserved": PricingModel.RESERVED,
    "spot": PricingModel.SPOT,
    "savingsplan": PricingModel.SAVINGS_PLAN,
}
