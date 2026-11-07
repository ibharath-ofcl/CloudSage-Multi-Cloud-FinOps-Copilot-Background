"""
CloudSage AWS Field & Service Category Mappings.
"""

from typing import Dict
from backend.app.core.enums import PricingModel, ServiceCategory

AWS_SERVICE_CATEGORY_MAP: Dict[str, ServiceCategory] = {
    # Compute
    "amazonec2": ServiceCategory.COMPUTE,
    "awslambda": ServiceCategory.COMPUTE,
    "amazonecs": ServiceCategory.COMPUTE,
    "amazoneks": ServiceCategory.COMPUTE,
    "fargate": ServiceCategory.COMPUTE,
    "lightsail": ServiceCategory.COMPUTE,
    "batch": ServiceCategory.COMPUTE,

    # Storage
    "amazons3": ServiceCategory.STORAGE,
    "amazonebs": ServiceCategory.STORAGE,
    "amazonglacier": ServiceCategory.STORAGE,
    "amazonelasticfilesystem": ServiceCategory.STORAGE,
    "backup": ServiceCategory.STORAGE,

    # Database
    "amazonrds": ServiceCategory.DATABASE,
    "amazondynamodb": ServiceCategory.DATABASE,
    "amazonelasticache": ServiceCategory.DATABASE,
    "amazonredshift": ServiceCategory.DATABASE,
    "amazonaurora": ServiceCategory.DATABASE,
    "amazonneptune": ServiceCategory.DATABASE,
    "amazondocumentdb": ServiceCategory.DATABASE,

    # Networking
    "amazonvpc": ServiceCategory.NETWORKING,
    "amazoncloudfront": ServiceCategory.NETWORKING,
    "amazonroute53": ServiceCategory.NETWORKING,
    "awselasticloadbalancing": ServiceCategory.NETWORKING,
    "natgateway": ServiceCategory.NETWORKING,
    "directconnect": ServiceCategory.NETWORKING,
    "globalaccelerator": ServiceCategory.NETWORKING,

    # AI & ML
    "amazonsagemaker": ServiceCategory.AI_ML,
    "amazonbedrock": ServiceCategory.AI_ML,
    "amazontextract": ServiceCategory.AI_ML,
    "amazonrekognition": ServiceCategory.AI_ML,
    "amazoncomprehend": ServiceCategory.AI_ML,

    # Analytics
    "amazonathena": ServiceCategory.ANALYTICS,
    "amazonemr": ServiceCategory.ANALYTICS,
    "amazonkinesis": ServiceCategory.ANALYTICS,
    "amazonquicksight": ServiceCategory.ANALYTICS,
    "awsglue": ServiceCategory.ANALYTICS,

    # Management
    "amazoncloudwatch": ServiceCategory.MANAGEMENT,
    "awscloudtrail": ServiceCategory.MANAGEMENT,
    "awsconfig": ServiceCategory.MANAGEMENT,
    "awsorganizations": ServiceCategory.MANAGEMENT,

    # Security
    "awskms": ServiceCategory.SECURITY,
    "awswaf": ServiceCategory.SECURITY,
    "awsshield": ServiceCategory.SECURITY,
    "awssecretsmanager": ServiceCategory.SECURITY,
    "guardduty": ServiceCategory.SECURITY,
}

AWS_PRICING_MODEL_MAP: Dict[str, PricingModel] = {
    "usage": PricingModel.ON_DEMAND,
    "ondemand": PricingModel.ON_DEMAND,
    "savingsplancoveredusage": PricingModel.SAVINGS_PLAN,
    "savingsplanrecurringfee": PricingModel.SAVINGS_PLAN,
    "discountedusage": PricingModel.RESERVED,
    "rirecurringfee": PricingModel.RESERVED,
    "spot": PricingModel.SPOT,
}
