"""
CloudSage Resource Topology & Cross-Signal Correlation Engine.
Maps cloud resource topology via ResourceRelationship, queries time-series
telemetry utilization metrics via ResourceMetric, and discovers corroborating
signals across Waste Detections, FinOps Recommendations, and Alert Instances.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.core.enums import ConfidenceCategory
from backend.app.models.alert import AlertInstance
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.inventory import ResourceRelationship
from backend.app.models.recommendation import Recommendation
from backend.app.models.resource import CloudResource, ResourceMetric
from backend.app.models.waste import WasteDetection
from backend.app.schemas.investigation import (
    CrossSignalCorrelationResponse,
    ResourceInvestigationItem,
    ResourceInvestigationResponse,
)


class ResourceCorrelationEngine:
    """Correlates anomaly events with resource inventory, topology, and cross-engine signals."""

    @classmethod
    def get_resource_investigation(
        cls,
        db: Session,
        anomaly: CostAnomaly,
        investigation_id: UUID,
    ) -> ResourceInvestigationResponse:
        """
        Retrieves detailed resource context, topology edges, and telemetry summary.
        """
        resource_ids = set()
        if anomaly.resource_id:
            resource_ids.add(anomaly.resource_id)

        # Also find any resources in anomaly contributing resources
        if isinstance(anomaly.contributing_resources, list):
            for cr in anomaly.contributing_resources:
                if isinstance(cr, dict) and "resource_id" in cr:
                    resource_ids.add(cr["resource_id"])
                elif isinstance(cr, str):
                    resource_ids.add(cr)

        items: List[ResourceInvestigationItem] = []

        if resource_ids:
            resources = db.query(CloudResource).filter(CloudResource.resource_id.in_(resource_ids)).all()
        else:
            resources = []

        if not resources:
            # Fallback synthetic representation if resource inventory is still syncing
            res_id = anomaly.resource_id or f"{anomaly.service_name}-primary-resource"
            items.append(
                ResourceInvestigationItem(
                    resource_id=res_id,
                    resource_name=anomaly.resource_id or f"{anomaly.service_name} Resource",
                    resource_type=f"{anomaly.provider.lower()}:{anomaly.service_category.lower()}",
                    provider=anomaly.provider,
                    region=anomaly.region,
                    owner="unassigned",
                    environment="production",
                    cost_center="CC-UNALLOCATED",
                    actual_cost=anomaly.actual_cost,
                    excess_cost=anomaly.estimated_excess_cost,
                    contribution_percentage=Decimal("100.00"),
                    status="active",
                    metrics_summary={"status": "NO_TELEMETRY_RECORDED"},
                    relationships=[],
                )
            )
        else:
            for r in resources:
                # 1. Fetch metrics
                metrics = (
                    db.query(ResourceMetric)
                    .filter(ResourceMetric.resource_id == r.resource_id)
                    .order_by(ResourceMetric.timestamp.desc())
                    .limit(20)
                    .all()
                )
                metrics_summary = cls._summarize_metrics(metrics)

                # 2. Fetch topology relationships
                relations = (
                    db.query(ResourceRelationship)
                    .filter(
                        (ResourceRelationship.source_resource_id == r.resource_id) |
                        (ResourceRelationship.target_resource_id == r.resource_id)
                    )
                    .all()
                )
                rel_list = [
                    {
                        "source": rel.source_resource_id,
                        "target": rel.target_resource_id,
                        "type": rel.relationship_type,
                        "confidence": float(rel.confidence),
                    }
                    for rel in relations
                ]

                items.append(
                    ResourceInvestigationItem(
                        resource_id=r.resource_id,
                        resource_name=r.resource_name or r.resource_id,
                        resource_type=r.resource_type,
                        provider=r.provider,
                        region=r.region,
                        owner=r.owner or "unassigned",
                        environment=r.environment or "production",
                        cost_center=r.cost_center or "unallocated",
                        actual_cost=r.monthly_cost or anomaly.actual_cost,
                        excess_cost=anomaly.estimated_excess_cost,
                        contribution_percentage=Decimal("100.00"),
                        status=r.status or "active",
                        metrics_summary=metrics_summary,
                        relationships=rel_list,
                    )
                )

        return ResourceInvestigationResponse(
            investigation_id=investigation_id,
            total_affected_resources=len(items),
            resources=items,
        )

    @classmethod
    def get_cross_signals(
        cls,
        db: Session,
        anomaly: CostAnomaly,
        investigation_id: UUID,
    ) -> CrossSignalCorrelationResponse:
        """
        Discovers related waste detections, recommendations, and alert instances.
        """
        target_res_id = anomaly.resource_id

        # 1. Correlate Waste Detections
        waste_query = db.query(WasteDetection)
        if target_res_id:
            waste_query = waste_query.filter(
                (WasteDetection.resource_id == target_res_id) |
                (WasteDetection.provider == anomaly.provider)
            )
        else:
            waste_query = waste_query.filter(WasteDetection.provider == anomaly.provider)
        waste_items = waste_query.limit(10).all()

        correlated_waste = [
            {
                "id": str(w.id),
                "rule_name": w.detector_id or w.finding_title or w.waste_type,
                "waste_type": w.waste_type,
                "wasted_cost": float(w.estimated_monthly_waste),
                "severity": str(w.severity),
                "status": str(w.status),
            }
            for w in waste_items
        ]

        # 2. Correlate Recommendations
        rec_query = db.query(Recommendation)
        if target_res_id:
            rec_query = rec_query.filter(
                (Recommendation.resource_id == target_res_id) |
                (Recommendation.service_name == anomaly.service_name)
            )
        else:
            rec_query = rec_query.filter(Recommendation.service_name == anomaly.service_name)
        rec_items = rec_query.limit(10).all()

        correlated_recs = [
            {
                "id": str(rc.id),
                "title": rc.title,
                "strategy": rc.strategy_id,
                "estimated_monthly_savings": float(rc.estimated_monthly_savings),
                "priority": str(rc.priority),
                "status": str(rc.status),
            }
            for rc in rec_items
        ]

        # 3. Correlate Alerts
        alert_query = db.query(AlertInstance).filter(AlertInstance.anomaly_id == anomaly.id)
        alert_items = alert_query.limit(10).all()

        correlated_alerts = [
            {
                "id": str(al.id),
                "rule_name": al.title,
                "severity": al.severity,
                "status": al.status,
                "trigger_value": float(al.excess_cost),
            }
            for al in alert_items
        ]

        # Assess correlation confidence
        signal_count = len(correlated_waste) + len(correlated_recs) + len(correlated_alerts)
        if signal_count >= 3:
            conf = ConfidenceCategory.HIGH.value
            summary = (
                f"High multi-signal correlation: Found {len(correlated_waste)} waste detection(s), "
                f"{len(correlated_recs)} recommendation(s), and {len(correlated_alerts)} enterprise alert(s) "
                f"corroborating this cost event."
            )
        elif signal_count >= 1:
            conf = ConfidenceCategory.MEDIUM.value
            summary = (
                f"Moderate correlation: Cross-signal analysis identified {signal_count} related FinOps event(s) "
                f"in CloudSage."
            )
        else:
            conf = ConfidenceCategory.LOW.value
            summary = "Isolated cost event: No concurrent waste detections or active recommendations currently match this scope."

        return CrossSignalCorrelationResponse(
            investigation_id=investigation_id,
            correlated_waste_detections=correlated_waste,
            correlated_recommendations=correlated_recs,
            correlated_alerts=correlated_alerts,
            correlation_confidence=conf,
            correlation_summary=summary,
        )

    @classmethod
    def _summarize_metrics(cls, metrics: List[ResourceMetric]) -> Dict[str, Any]:
        """Summarizes CPU, Memory, and Disk/IOPS metrics."""
        if not metrics:
            return {"status": "NO_RECENT_SAMPLES"}

        cpu_vals = [m.average_value for m in metrics if "cpu" in (m.metric_name or "").lower() and m.average_value is not None]
        mem_vals = [m.average_value for m in metrics if "mem" in (m.metric_name or "").lower() and m.average_value is not None]

        summary: Dict[str, Any] = {"sample_count": len(metrics)}
        if cpu_vals:
            summary["avg_cpu_percent"] = float(sum(cpu_vals) / Decimal(str(len(cpu_vals))))
            summary["max_cpu_percent"] = float(max(cpu_vals))
            summary["min_cpu_percent"] = float(min(cpu_vals))

        if mem_vals:
            summary["avg_memory_percent"] = float(sum(mem_vals) / Decimal(str(len(mem_vals))))
            summary["max_memory_percent"] = float(max(mem_vals))

        return summary
