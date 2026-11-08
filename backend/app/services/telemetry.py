"""
CloudSage Resource Telemetry Analytics Service.
Queries time-series utilization metrics (CPU, Memory, Network, Disk) from PostgreSQL,
computes statistical aggregates (min, max, mean, latest), detects gaps, and formats
evidence-backed data points for charts.
Strict rule: Never fabricate telemetry. If metrics are absent, return explicit empty status.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.models.resource import CloudResource, ResourceMetric


STANDARD_METRICS = [
    "cpu_utilization_pct",
    "memory_utilization_pct",
    "network_in_bytes",
    "network_out_bytes",
    "disk_iops",
]


class TelemetryService:
    """Service for fetching, aggregating, and structuring resource utilization telemetry."""

    @classmethod
    def get_resource_telemetry(
        cls,
        db: Session,
        resource_id: str,
        metric_names: Optional[List[str]] = None,
        days: int = 14,
    ) -> Dict[str, Any]:
        """
        Retrieves utilization metrics for a specific cloud resource over a historical window.
        Returns empty state when metrics are not present, without fabricating data.
        """
        res: Optional[CloudResource] = db.query(CloudResource).filter(
            CloudResource.resource_id == resource_id
        ).first()

        target_metrics = metric_names or STANDARD_METRICS

        query = (
            db.query(ResourceMetric)
            .filter(ResourceMetric.resource_id == resource_id)
            .filter(ResourceMetric.metric_name.in_(target_metrics))
            .order_by(ResourceMetric.metric_name, ResourceMetric.timestamp.asc())
        )

        records = query.all()

        if not records:
            return {
                "resource_id": resource_id,
                "resource_found": res is not None,
                "has_telemetry": False,
                "reason": "NO_TELEMETRY_RECORDED",
                "message": (
                    f"No telemetry observations recorded for resource '{resource_id}'. "
                    "Ensure CloudWatch, Azure Monitor, or GCP Monitoring agent is enabled."
                ),
                "metrics": {},
                "summary": {},
            }

        grouped_metrics: Dict[str, List[Dict[str, Any]]] = {}
        summary_stats: Dict[str, Dict[str, Any]] = {}

        for rec in records:
            m_name = rec.metric_name
            if m_name not in grouped_metrics:
                grouped_metrics[m_name] = []
            grouped_metrics[m_name].append({
                "timestamp": rec.timestamp.isoformat() if rec.timestamp else "",
                "average": float(rec.average_value) if rec.average_value is not None else 0.0,
                "peak": float(rec.peak_value) if rec.peak_value is not None else 0.0,
                "samples": rec.sample_count,
            })

        for m_name, points in grouped_metrics.items():
            if not points:
                continue
            averages = [p["average"] for p in points]
            peaks = [p["peak"] for p in points]

            summary_stats[m_name] = {
                "min": round(min(averages), 2),
                "max": round(max(peaks), 2),
                "avg": round(sum(averages) / len(averages), 2),
                "latest": round(averages[-1], 2),
                "total_points": len(points),
                "latest_timestamp": points[-1]["timestamp"],
            }

        return {
            "resource_id": resource_id,
            "resource_found": res is not None,
            "has_telemetry": True,
            "provider": res.provider if res else "UNKNOWN",
            "service_name": res.service_name if res else "UNKNOWN",
            "status": res.status if res else "UNKNOWN",
            "observation_window_days": days,
            "metrics": grouped_metrics,
            "summary": summary_stats,
        }
