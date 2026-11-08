"""
CloudSage Unified Entity Correlation Service.
Builds an integrated correlation view linking Cloud Resources, Waste Detections,
Optimization Recommendations, Cost Anomalies, Billing Records, and Telemetry.
Enforces strict anti-double-counting guarantees with clear financial taxonomy.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.anomaly import CostAnomaly
from backend.app.models.billing import BillingRecord
from backend.app.models.recommendation import Recommendation
from backend.app.models.resource import CloudResource
from backend.app.models.waste import WasteDetection
from backend.app.services.telemetry import TelemetryService


class CorrelationService:
    """Provides multi-entity correlation and financial impact alignment."""

    @classmethod
    def get_resource_correlations(
        cls,
        db: Session,
        resource_id: str,
    ) -> Dict[str, Any]:
        """
        Retrieves all correlated FinOps entities for a given resource ID:
        waste findings, active recommendations, anomalies, and billing history.
        """
        res: Optional[CloudResource] = db.query(CloudResource).filter(
            CloudResource.resource_id == resource_id
        ).first()

        # 1. Correlated Waste Detections
        waste_items = db.query(WasteDetection).filter(
            WasteDetection.resource_id == resource_id
        ).all()

        # 2. Correlated Recommendations
        rec_items = db.query(Recommendation).filter(
            Recommendation.resource_id == resource_id
        ).all()

        # 3. Correlated Anomalies (by resource_id or matching service/account)
        anomalies = db.query(CostAnomaly).filter(
            CostAnomaly.resource_id == resource_id
        ).all()

        # 4. Recent Billing Records
        billing_query = db.query(BillingRecord).filter(
            BillingRecord.resource_id == resource_id
        ).order_by(BillingRecord.usage_start_time.desc()).limit(10)
        billing_records = billing_query.all()

        # 5. Telemetry
        telemetry = TelemetryService.get_resource_telemetry(db, resource_id=resource_id)

        # Financial buckets (Anti-Double-Counting)
        monthly_spend = res.monthly_cost if res else Decimal("0.0000")
        active_waste = sum((w.estimated_monthly_waste for w in waste_items if w.status in ("ACTIVE", "OPEN", "ACKNOWLEDGED")), Decimal("0.0000"))
        potential_savings = sum((r.estimated_monthly_savings for r in rec_items if r.status not in ("DISMISSED", "REJECTED")), Decimal("0.0000"))
        realized_savings = sum((r.verified_savings for r in rec_items if r.status == "VERIFIED" and r.verified_savings), Decimal("0.0000"))

        return {
            "resource_id": resource_id,
            "resource_exists": res is not None,
            "resource": {
                "resource_id": res.resource_id if res else resource_id,
                "provider": res.provider if res else "UNKNOWN",
                "service_name": res.service_name if res else "UNKNOWN",
                "account_id": res.account_id if res else "UNKNOWN",
                "region": res.region if res else "UNKNOWN",
                "environment": res.environment if res else "unknown",
                "owner": res.owner if res else "unassigned",
                "status": res.status if res else "unknown",
                "monthly_cost": float(monthly_spend),
                "tags": res.tags if res else {},
            } if res else None,
            "financial_taxonomy": {
                "currency": "USD",
                "baseline_monthly_spend": float(monthly_spend),
                "active_monthly_waste": float(active_waste),
                "potential_monthly_savings": float(potential_savings),
                "verified_realized_savings": float(realized_savings),
                "anti_double_counting_note": (
                    "Baseline spend represents historical billed cost. Waste represents avoidable cost. "
                    "Potential savings represents projected reduction. Do not add waste and savings together."
                ),
            },
            "waste_findings": [
                {
                    "id": str(w.id),
                    "waste_type": w.waste_type,
                    "finding_title": w.finding_title,
                    "severity": w.severity,
                    "status": w.status,
                    "assigned_to": w.assigned_to,
                    "estimated_monthly_waste": float(w.estimated_monthly_waste),
                    "confidence_score": float(w.confidence_score),
                    "first_detected_at": w.first_detected_at.isoformat() if w.first_detected_at else None,
                }
                for w in waste_items
            ],
            "recommendations": [
                {
                    "id": str(r.id),
                    "title": r.title,
                    "action_type": r.action_type,
                    "priority": r.priority,
                    "status": r.status,
                    "assigned_to": r.assigned_to,
                    "estimated_monthly_savings": float(r.estimated_monthly_savings),
                    "revised_monthly_savings": float(r.revised_monthly_savings) if r.revised_monthly_savings else None,
                    "is_savings_overridden": r.is_savings_overridden,
                    "risk_level": r.risk_level,
                }
                for r in rec_items
            ],
            "anomalies": [
                {
                    "id": str(a.id),
                    "title": a.title,
                    "severity": a.severity,
                    "status": a.status,
                    "actual_cost": float(a.actual_cost),
                    "expected_cost": float(a.expected_cost),
                    "cost_impact": float(getattr(a, "estimated_excess_cost", 0) or getattr(a, "absolute_deviation", 0) or 0),
                    "detected_at": a.detected_at.isoformat() if a.detected_at else None,
                }
                for a in anomalies
            ],
            "billing_records": [
                {
                    "id": str(b.id),
                    "charge_period_start": b.usage_start_time.isoformat() if b.usage_start_time else None,
                    "billed_cost": float(b.billed_cost),
                    "effective_cost": float(b.effective_cost),
                    "pricing_category": b.pricing_category,
                }
                for b in billing_records
            ],
            "telemetry_summary": telemetry.get("summary", {}),
            "has_telemetry": telemetry.get("has_telemetry", False),
        }
