"""
Tests for Idle Compute and Oversized Compute Detectors.
Validates multi-cloud CPU, network safeguards, observation windows, and confidence scoring.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from backend.app.core.enums import CloudProvider, Severity, WasteType
from backend.app.models.billing import BillingRecord
from backend.app.models.resource import CloudResource, ResourceMetric
from backend.app.waste_detection.detectors.idle_compute import IdleComputeDetector
from backend.app.waste_detection.detectors.oversized_compute import OversizedComputeDetector


def test_idle_compute_detector_aws_ec2_flagged():
    detector = IdleComputeDetector()
    now = datetime.now(timezone.utc)

    resource = CloudResource(
        resource_id="i-0123456789abcdef0",
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        resource_name="dev-worker-node",
        status="running",
        monthly_cost=Decimal("72.5000"),
        first_discovered_at=now - timedelta(days=30),
        last_seen_at=now,
    )

    # 7 daily metrics with avg CPU 2.5%, max CPU 8.0%, low network
    metrics = []
    for day in range(7):
        ts = now - timedelta(days=day)
        metrics.extend([
            ResourceMetric(
                resource_id=resource.resource_id,
                timestamp=ts,
                metric_name="cpu_utilization_pct",
                average_value=Decimal("2.50"),
                peak_value=Decimal("8.00"),
            ),
            ResourceMetric(
                resource_id=resource.resource_id,
                timestamp=ts,
                metric_name="network_in_bytes",
                average_value=Decimal("1048576"),
                peak_value=Decimal("2097152"),
            ),
        ])

    result = detector.detect(resource=resource, metrics=metrics, relationships=[], billing_records=[])
    assert result.status == "DETECTED"
    assert result.finding is not None
    assert result.finding.waste_type == WasteType.IDLE_COMPUTE
    assert result.finding.estimated_monthly_savings == Decimal("72.5000")
    assert result.finding.severity == Severity.MEDIUM
    assert result.finding.confidence_score >= Decimal("0.6000")
    assert result.finding.evidence["avg_cpu_utilization_pct"] == 2.5


def test_idle_compute_conflicting_network_safeguard():
    """An instance with low CPU (<5%) but heavy network traffic (>50MB/day) is an active proxy/gateway and must be CLEAN."""
    detector = IdleComputeDetector()
    now = datetime.now(timezone.utc)

    resource = CloudResource(
        resource_id="i-proxy-gateway-01",
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        resource_name="nat-proxy",
        status="running",
        monthly_cost=Decimal("120.0000"),
    )

    # Low CPU but high network (60 MB/day)
    metrics = []
    for day in range(7):
        ts = now - timedelta(days=day)
        metrics.extend([
            ResourceMetric(
                resource_id=resource.resource_id,
                timestamp=ts,
                metric_name="cpu_utilization_pct",
                average_value=Decimal("3.00"),
                peak_value=Decimal("7.00"),
            ),
            ResourceMetric(
                resource_id=resource.resource_id,
                timestamp=ts,
                metric_name="network_in_bytes",
                average_value=Decimal("62914560"),  # 60 MB
                peak_value=Decimal("70000000"),
            ),
        ])

    result = detector.detect(resource=resource, metrics=metrics, relationships=[], billing_records=[])
    assert result.status == "CLEAN"
    assert result.finding is None


def test_idle_compute_insufficient_observation_window():
    """Instances with fewer than ~3 days of observation span must yield INSUFFICIENT_DATA."""
    detector = IdleComputeDetector()
    now = datetime.now(timezone.utc)

    resource = CloudResource(
        resource_id="i-new-instance-02",
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        resource_name="new-service",
        status="running",
        monthly_cost=Decimal("50.0000"),
    )

    # Only 1 day span
    metrics = [
        ResourceMetric(
            resource_id=resource.resource_id,
            timestamp=now - timedelta(hours=h),
            metric_name="cpu_utilization_pct",
            average_value=Decimal("1.00"),
            peak_value=Decimal("2.00"),
        )
        for h in range(12)
    ]

    result = detector.detect(resource=resource, metrics=metrics, relationships=[], billing_records=[])
    assert result.status == "INSUFFICIENT_DATA"
    assert result.finding is None


def test_oversized_compute_detector_azure_vm():
    """Detects oversized VM with avg CPU < 20% and peak < 50% over 14-day window with 50% downsize savings."""
    detector = OversizedComputeDetector()
    now = datetime.now(timezone.utc)

    resource = CloudResource(
        resource_id="/subscriptions/sub-123/resourceGroups/rg-prod/providers/Microsoft.Compute/virtualMachines/app-vm-01",
        provider="AZURE",
        account_id="sub-123",
        region="eastus",
        service_category="COMPUTE",
        service_name="Azure Virtual Machines",
        resource_type="Microsoft.Compute/virtualMachines",
        resource_name="app-vm-01",
        status="running",
        monthly_cost=Decimal("200.0000"),
    )

    metrics = []
    for day in range(14):
        ts = now - timedelta(days=day)
        metrics.extend([
            ResourceMetric(
                resource_id=resource.resource_id,
                timestamp=ts,
                metric_name="Percentage CPU",
                average_value=Decimal("12.00"),
                peak_value=Decimal("38.00"),
            ),
        ])

    result = detector.detect(resource=resource, metrics=metrics, relationships=[], billing_records=[])
    assert result.status == "DETECTED"
    assert result.finding is not None
    assert result.finding.waste_type == WasteType.OVERSIZED_COMPUTE
    # 50% conservative downsize savings
    assert result.finding.estimated_monthly_savings == Decimal("100.0000")
    assert result.finding.severity == Severity.MEDIUM
