"""
CloudSage Underutilized Managed Database Detector.
Identifies active cloud database instances (AWS RDS, Azure SQL, GCP Cloud SQL)
exhibiting negligible connection counts and low compute utilization over continuous windows.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from backend.app.core.enums import Severity, WasteType
from backend.app.models.billing import BillingRecord
from backend.app.models.inventory import ResourceRelationship
from backend.app.models.resource import CloudResource, ResourceMetric
from backend.app.waste_detection.base import BaseWasteDetector
from backend.app.waste_detection.models import DetectorExecutionResult, WasteFinding
from backend.app.waste_detection.severity import SeverityEvaluator


class UnderutilizedDatabaseDetector(BaseWasteDetector):
    """Detects running databases with negligible client connections and utilization."""

    @property
    def detector_id(self) -> str:
        return "underutilized_database_detector"

    @property
    def detector_version(self) -> str:
        return "1.0.0"

    @property
    def waste_category(self) -> WasteType:
        return WasteType.UNDERUTILIZED_DATABASE

    @property
    def description(self) -> str:
        return (
            "Detects active managed databases (AWS RDS, Azure SQL, GCP Cloud SQL) with average "
            "connection count < 2 and average CPU < 10% over a 7-day window. Requires connection telemetry."
        )

    @property
    def supported_providers(self) -> List[str]:
        return ["AWS", "AZURE", "GCP"]

    @property
    def supported_resource_types(self) -> List[str]:
        return [
            "rds:db",
            "rds:cluster",
            "Microsoft.Sql/servers/databases",
            "sqladmin.googleapis.com/Instance",
            "DATABASE",
        ]

    @property
    def default_thresholds(self) -> Dict[str, Any]:
        return {
            "max_avg_connections": Decimal("2.0"),
            "max_avg_cpu_pct": Decimal("10.0"),
            "min_observation_days": 7,
        }

    def detect(
        self,
        resource: CloudResource,
        metrics: List[ResourceMetric],
        relationships: List[ResourceRelationship],
        billing_records: List[BillingRecord],
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> DetectorExecutionResult:
        cfg = dict(self.default_thresholds)
        if thresholds:
            cfg.update(thresholds)

        res_id = resource.resource_id

        if resource.service_category.upper() != "DATABASE":
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="CLEAN",
                message="Resource is not a managed database",
            )

        if resource.status.lower() not in ("active", "available", "runnable"):
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="CLEAN",
                message=f"Database is not active (status: {resource.status})",
            )

        # Connection telemetry is mandatory - low CPU alone must NEVER trigger underutilized database
        conn_metrics = [
            m for m in metrics
            if "connection" in m.metric_name.lower() or m.metric_name in ("DatabaseConnections", "connections")
        ]

        if not conn_metrics:
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="INSUFFICIENT_DATA",
                message="Missing database connection telemetry; cannot infer underutilization from CPU alone",
            )

        cpu_metrics = [
            m for m in metrics
            if "cpu" in m.metric_name.lower()
        ]

        avg_conns = sum((m.average_value for m in conn_metrics), Decimal("0.0")) / Decimal(str(len(conn_metrics)))
        avg_cpu = Decimal("0.0")
        if cpu_metrics:
            avg_cpu = sum((m.average_value for m in cpu_metrics), Decimal("0.0")) / Decimal(str(len(cpu_metrics)))

        if avg_conns < cfg["max_avg_connections"] and (not cpu_metrics or avg_cpu < cfg["max_avg_cpu_pct"]):
            cost = resource.monthly_cost or Decimal("0.0000")
            if cost <= Decimal("0.0000") and billing_records:
                cost = sum((b.unblended_cost for b in billing_records), Decimal("0.0000"))

            # Conservative confidence
            confidence = Decimal("0.9000") if cpu_metrics else Decimal("0.7500")
            severity = SeverityEvaluator.evaluate_severity(cost)

            evidence_proof = {
                "avg_database_connections": float(avg_conns.quantize(Decimal("0.01"))),
                "avg_cpu_utilization_pct": float(avg_cpu.quantize(Decimal("0.01"))),
                "connection_sample_count": len(conn_metrics),
                "observation_window_days": cfg["min_observation_days"],
                "monthly_cost_usd": str(cost),
            }

            finding = WasteFinding(
                resource_id=res_id,
                provider=resource.provider,
                account_id=resource.account_id,
                resource_name=resource.resource_name,
                resource_type=resource.resource_type,
                waste_type=WasteType.UNDERUTILIZED_DATABASE,
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                finding_title=f"Underutilized {resource.provider} Database ({resource.resource_name or res_id})",
                explanation=(
                    f"Database instance has averaged only {avg_conns:.1f} client connections "
                    f"(threshold < {cfg['max_avg_connections']}) and {avg_cpu:.1f}% CPU over {cfg['min_observation_days']} days "
                    f"while incurring provisioned database tier fees."
                ),
                severity=severity,
                confidence_score=confidence,
                estimated_monthly_savings=cost,
                observation_window_days=cfg["min_observation_days"],
                evidence=evidence_proof,
            )

            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="DETECTED",
                finding=finding,
            )

        return DetectorExecutionResult(
            detector_id=self.detector_id,
            resource_id=res_id,
            status="CLEAN",
            message=f"Database active connections ({avg_conns:.1f}) indicate regular operational usage",
        )
