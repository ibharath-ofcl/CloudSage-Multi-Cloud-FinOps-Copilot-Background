"""
CloudSage Synthetic Scenarios.
Defines reproducible simulation scenarios for test fixtures and future waste/anomaly detection benchmarks.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ScenarioDefinition:
    name: str
    code: str
    description: str
    characteristics: Dict[str, any]


SCENARIOS = {
    "normal": ScenarioDefinition(
        name="Normal Cloud Expenditure",
        code="SCENARIO_A",
        description="Standard production infrastructure with stable day-over-day costs and typical utilization.",
        characteristics={"waste_ratio": 0.0, "spike_multiplier": 1.0, "tagging_rate": 0.95}
    ),
    "idle_vm": ScenarioDefinition(
        name="Idle VM Waste",
        code="SCENARIO_B",
        description="Compute instances (EC2, Azure VM, GCP Compute Engine) running with average CPU < 5% over 7+ days.",
        characteristics={"waste_ratio": 0.25, "idle_cpu_max": 4.5, "network_io_mb_day": 1.2}
    ),
    "unattached_storage": ScenarioDefinition(
        name="Unattached Storage Disks",
        code="SCENARIO_C",
        description="Block storage volumes (EBS, Azure Managed Disks, GCP Persistent Disks) in available/unattached state > 3 days.",
        characteristics={"waste_ratio": 0.20, "unattached_days": 14}
    ),
    "oversized_compute": ScenarioDefinition(
        name="Oversized Compute Instances",
        code="SCENARIO_D",
        description="Large instances (e.g. c5.4xlarge, Standard_D8s_v5) whose peak CPU stays under 15% and memory under 20%.",
        characteristics={"waste_ratio": 0.30, "peak_cpu": 12.0, "downsizing_target": "c5.large"}
    ),
    "cost_spike": ScenarioDefinition(
        name="Unexpected Cost Increase",
        code="SCENARIO_E",
        description="Sudden 300% to 500% surge in daily spending driven by log ingestion or unpartitioned BigQuery queries.",
        characteristics={"spike_multiplier": 4.5, "affected_service": "Analytics/Logs"}
    ),
    "poor_tagging": ScenarioDefinition(
        name="Poorly Tagged Resources",
        code="SCENARIO_F",
        description="Infrastructure provisioned without mandatory 'owner', 'environment', or 'costcenter' tags.",
        characteristics={"missing_tags_rate": 0.80}
    ),
}
