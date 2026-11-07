"""
Evidence Citation Generator for CloudSage AI FinOps Copilot.
Transforms raw query execution records and metrics into traceable,
structured citations referencing canonical Stage 3–8 database rows.
"""

from typing import Any, Dict, List
from backend.app.copilot.schemas import EvidenceCitationSchema


class CitationBuilder:
    """Builds structured EvidenceCitationSchema objects from database query results."""

    @classmethod
    def build_citations(
        cls,
        target_dataset: str,
        sample_records: List[Dict[str, Any]],
    ) -> List[EvidenceCitationSchema]:
        """Converts sample database records into evidence citations."""
        citations: List[EvidenceCitationSchema] = []

        for record in sample_records:
            rec_id = str(record.get("id") or "")
            provider = record.get("provider", "Cloud")

            if target_dataset == "billing_records":
                service = record.get("service", "Service")
                cost = record.get("unblended_cost", "0.0000")
                curr = record.get("currency", "USD")
                res_id = record.get("resource_id", "N/A")
                citations.append(
                    EvidenceCitationSchema(
                        source_table="billing_records",
                        record_id=rec_id,
                        description=f"FOCUS Normalized Billing: {provider} {service} (Resource: {res_id})",
                        metric_value=f"${cost} {curr}",
                        confidence=1.0,
                    )
                )

            elif target_dataset == "cost_anomalies":
                cat = record.get("category", "ANOMALY")
                service = record.get("service", "Service")
                excess = record.get("excess_cost", "0.0000")
                severity = record.get("severity", "HIGH")
                citations.append(
                    EvidenceCitationSchema(
                        source_table="cost_anomalies",
                        record_id=rec_id,
                        description=f"Stage 7 Anomaly: {provider} {service} ({cat}, Severity: {severity})",
                        metric_value=f"${excess} excess",
                        confidence=0.95,
                    )
                )

            elif target_dataset == "waste_detections":
                w_type = record.get("waste_type", "WASTE")
                res_id = record.get("resource_id", "N/A")
                waste_cost = record.get("monthly_waste", "0.0000")
                severity = record.get("severity", "MEDIUM")
                citations.append(
                    EvidenceCitationSchema(
                        source_table="waste_detections",
                        record_id=rec_id,
                        description=f"Stage 6 Waste Detection: {provider} {w_type} (Resource: {res_id}, Severity: {severity})",
                        metric_value=f"${waste_cost}/month waste",
                        confidence=0.98,
                    )
                )

            elif target_dataset == "recommendations":
                title = record.get("title", "Optimization Recommendation")
                strategy = record.get("strategy", "Strategy")
                monthly = record.get("monthly_savings", "0.0000")
                priority = record.get("priority", "HIGH")
                citations.append(
                    EvidenceCitationSchema(
                        source_table="recommendations",
                        record_id=rec_id,
                        description=f"Stage 8 Recommendation: [{priority}] {title} ({strategy})",
                        metric_value=f"${monthly}/month savings",
                        confidence=1.0,
                    )
                )

            elif target_dataset == "cloud_resources":
                name = record.get("resource_name") or rec_id
                r_type = record.get("resource_type", "Resource")
                region = record.get("region", "Global")
                status = record.get("status", "ACTIVE")
                citations.append(
                    EvidenceCitationSchema(
                        source_table="cloud_resources",
                        record_id=rec_id,
                        description=f"Stage 5 Inventory: {provider} {r_type} '{name}' in {region} (Status: {status})",
                        metric_value=status,
                        confidence=1.0,
                    )
                )

        return citations

