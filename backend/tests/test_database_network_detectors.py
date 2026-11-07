"""
Tests for Underutilized Managed Database and Unused Network Resource Detectors.
Validates connection telemetry mandate, low-CPU busy DB safeguards, unassociated IPs, and zero-target load balancers.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from backend.app.core.enums import Severity, WasteType
from backend.app.models.inventory import ResourceRelationship
from backend.app.models.resource import CloudResource, ResourceMetric
from backend.app.waste_detection.detectors.underutilized_database import UnderutilizedDatabaseDetector
from backend.app.waste_detection.detectors.unused_network_resources import UnusedNetworkResourcesDetector


def test_underutilized_database_flagged():
    """Database with avg connections < 2 and avg CPU < 10% is flagged as underutilized."""
    detector = UnderutilizedDatabaseDetector()
    now = datetime.now(timezone.utc)

    resource = CloudResource(
        resource_id="arn:aws:rds:us-east-1:112233445566:db:dev-postgres-db",
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="DATABASE",
        service_name="AmazonRDS",
        resource_type="rds:db",
        resource_name="dev-postgres-db",
        status="available",
        monthly_cost=Decimal("180.0000"),
        first_discovered_at=now - timedelta(days=30),
        last_seen_at=now,
    )

    metrics = []
    for day in range(7):
        ts = now - timedelta(days=day)
        metrics.extend([
            ResourceMetric(
                resource_id=resource.resource_id,
                timestamp=ts,
                metric_name="DatabaseConnections",
                average_value=Decimal("0.5"),
                peak_value=Decimal("1.0"),
            ),
            ResourceMetric(
                resource_id=resource.resource_id,
                timestamp=ts,
                metric_name="cpu_utilization_pct",
                average_value=Decimal("4.0"),
                peak_value=Decimal("8.0"),
            ),
        ])

    result = detector.detect(resource=resource, metrics=metrics, relationships=[], billing_records=[])
    assert result.status == "DETECTED"
    assert result.finding is not None
    assert result.finding.waste_type == WasteType.UNDERUTILIZED_DATABASE
    assert result.finding.estimated_monthly_savings == Decimal("180.0000")
    assert result.finding.confidence_score >= Decimal("0.7500")


def test_underutilized_database_missing_connections_insufficient_data():
    """Low CPU alone must NEVER trigger underutilized database without connection metrics."""
    detector = UnderutilizedDatabaseDetector()
    now = datetime.now(timezone.utc)

    resource = CloudResource(
        resource_id="arn:aws:rds:us-east-1:112233445566:db:silent-db",
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="DATABASE",
        service_name="AmazonRDS",
        resource_type="rds:db",
        resource_name="silent-db",
        status="available",
        monthly_cost=Decimal("250.0000"),
        first_discovered_at=now - timedelta(days=30),
        last_seen_at=now,
    )

    # CPU metrics only, no connection metrics
    metrics = [
        ResourceMetric(
            resource_id=resource.resource_id,
            timestamp=now - timedelta(days=day),
            metric_name="cpu_utilization_pct",
            average_value=Decimal("2.0"),
            peak_value=Decimal("5.0"),
        )
        for day in range(7)
    ]

    result = detector.detect(resource=resource, metrics=metrics, relationships=[], billing_records=[])
    assert result.status == "INSUFFICIENT_DATA"
    assert result.finding is None


def test_active_database_busy_connections_clean():
    """Database with low CPU (<10%) but active connections (>20) is an active operational DB and must be CLEAN."""
    detector = UnderutilizedDatabaseDetector()
    now = datetime.now(timezone.utc)

    resource = CloudResource(
        resource_id="arn:aws:rds:us-east-1:112233445566:db:prod-read-replica",
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="DATABASE",
        service_name="AmazonRDS",
        resource_type="rds:db",
        resource_name="prod-read-replica",
        status="available",
        monthly_cost=Decimal("350.0000"),
        first_discovered_at=now - timedelta(days=30),
        last_seen_at=now,
    )

    metrics = []
    for day in range(7):
        ts = now - timedelta(days=day)
        metrics.extend([
            ResourceMetric(
                resource_id=resource.resource_id,
                timestamp=ts,
                metric_name="DatabaseConnections",
                average_value=Decimal("45.0"),
                peak_value=Decimal("120.0"),
            ),
            ResourceMetric(
                resource_id=resource.resource_id,
                timestamp=ts,
                metric_name="cpu_utilization_pct",
                average_value=Decimal("6.0"),
                peak_value=Decimal("12.0"),
            ),
        ])

    result = detector.detect(resource=resource, metrics=metrics, relationships=[], billing_records=[])
    assert result.status == "CLEAN"
    assert result.finding is None


def test_unused_elastic_ip_flagged():
    """Unassociated Elastic IP is flagged as unused network waste."""
    detector = UnusedNetworkResourcesDetector()
    now = datetime.now(timezone.utc)

    resource = CloudResource(
        resource_id="eipalloc-0123456789abcdef0",
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="NETWORKING",
        service_name="AmazonVPC",
        resource_type="ec2:eip",
        resource_name="unassociated-public-ip",
        status="available",
        monthly_cost=Decimal("3.6500"),
        first_discovered_at=now - timedelta(days=20),
        last_seen_at=now,
        resource_metadata={"association_id": None, "instance_id": None},
    )

    result = detector.detect(resource=resource, metrics=[], relationships=[], billing_records=[])
    assert result.status == "DETECTED"
    assert result.finding is not None
    assert result.finding.waste_type == WasteType.IDLE_IP
    assert result.finding.estimated_monthly_savings == Decimal("3.6500")


def test_zero_target_load_balancer_flagged():
    """Load balancer with 0 target backends is flagged as unused network waste."""
    detector = UnusedNetworkResourcesDetector()
    now = datetime.now(timezone.utc)

    resource = CloudResource(
        resource_id="arn:aws:elasticloadbalancing:us-east-1:112233445566:loadbalancer/app/orphaned-alb/50dc6c495c0c9188",
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="NETWORKING",
        service_name="ElasticLoadBalancing",
        resource_type="elasticloadbalancing:loadbalancer",
        resource_name="orphaned-alb",
        status="active",
        monthly_cost=Decimal("25.0000"),
        first_discovered_at=now - timedelta(days=20),
        last_seen_at=now,
        resource_metadata={"target_count": 0},
    )

    result = detector.detect(resource=resource, metrics=[], relationships=[], billing_records=[])
    assert result.status == "DETECTED"
    assert result.finding is not None
    assert result.finding.waste_type == WasteType.ZERO_TARGET_LB
    assert result.finding.estimated_monthly_savings == Decimal("25.0000")
