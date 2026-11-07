"""
CloudSage Conservative Financial Savings Calculator.
Computes estimated monthly and annualized cost reductions from verified billing records
using strict Decimal precision and auditable methodology metadata.
Zero float calculations permitted.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from backend.app.models.billing import BillingRecord
from backend.app.models.resource import CloudResource


class SavingsCalculator:
    """Calculates non-speculative, evidence-backed monthly waste savings."""

    @classmethod
    def estimate_idle_compute_savings(
        cls,
        resource: CloudResource,
        billing_records: List[BillingRecord],
    ) -> Tuple[Decimal, str, Dict[str, Any]]:
        """
        Estimates monthly savings for an idle virtual machine based on its recurring compute ledger.
        """
        # If resource has correlated monthly_cost from Stage 5, prioritize it
        monthly_cost = resource.monthly_cost or Decimal("0.0000")

        if monthly_cost > Decimal("0.0000"):
            methodology = "Correlated 30-day unblended compute ledger expenditure"
            details = {
                "source": "resource.monthly_cost",
                "evaluated_cost_usd": str(monthly_cost),
                "confidence_level": "HIGH",
            }
            return monthly_cost, methodology, details

        # Fallback to sum of provided billing records
        if billing_records:
            total_unblended = sum((b.unblended_cost for b in billing_records), Decimal("0.0000"))
            if total_unblended > Decimal("0.0000"):
                methodology = f"Aggregated {len(billing_records)} billing line items for resource"
                details = {
                    "source": "billing_records_sum",
                    "evaluated_cost_usd": str(total_unblended),
                    "confidence_level": "MEDIUM",
                }
                return total_unblended, methodology, details

        return Decimal("0.0000"), "Insufficient billing history to quantify financial savings", {"source": "NONE"}

    @classmethod
    def estimate_oversized_compute_savings(
        cls,
        resource: CloudResource,
        downsize_ratio: Decimal = Decimal("0.50"),
    ) -> Tuple[Decimal, str, Dict[str, Any]]:
        """
        Estimates savings from rightsizing an oversized compute instance to one size tier lower.
        Conservative default: 50% cost reduction of compute instance price.
        """
        base_cost = resource.monthly_cost or Decimal("0.0000")
        if base_cost <= Decimal("0.0000"):
            return Decimal("0.0000"), "Zero recurring compute spend detected", {"source": "NONE"}

        estimated_savings = (base_cost * downsize_ratio).quantize(Decimal("0.0001"))
        methodology = f"Conservative single-tier downsize ({int(downsize_ratio * 100)}% of current monthly spend)"
        details = {
            "source": "downsize_heuristic",
            "base_monthly_cost": str(base_cost),
            "ratio": str(downsize_ratio),
        }
        return estimated_savings, methodology, details

    @classmethod
    def estimate_unattached_storage_savings(
        cls,
        resource: CloudResource,
        billing_records: List[BillingRecord],
    ) -> Tuple[Decimal, str, Dict[str, Any]]:
        """
        Estimates savings from reclaiming an unattached volume.
        Since the volume is unattached, 100% of its storage expenditure is waste.
        """
        cost = resource.monthly_cost or Decimal("0.0000")
        if cost > Decimal("0.0000"):
            return cost, "100% of unattached storage provisioned monthly fee", {
                "source": "resource.monthly_cost",
                "size_gb": resource.resource_metadata.get("size_gb") if resource.resource_metadata else None,
            }

        # Estimate from capacity if available (e.g. $0.08 per GB-month for gp3/standard SSD)
        size_gb = None
        if resource.resource_metadata and "size_gb" in resource.resource_metadata:
            try:
                size_gb = Decimal(str(resource.resource_metadata["size_gb"]))
            except Exception:
                size_gb = None

        if size_gb and size_gb > Decimal("0.0"):
            # Standard block storage rate heuristic $0.08 / GB-mo
            est_cost = (size_gb * Decimal("0.0800")).quantize(Decimal("0.0001"))
            return est_cost, f"Estimated storage capacity tariff ($0.08/GB for {size_gb} GB)", {
                "source": "capacity_rate_estimate",
                "size_gb": str(size_gb),
            }

        return Decimal("0.0000"), "No billing records or disk size capacity found to estimate savings", {"source": "NONE"}

    @classmethod
    def estimate_orphaned_snapshot_savings(
        cls,
        resource: CloudResource,
        billing_records: List[BillingRecord],
    ) -> Tuple[Decimal, str, Dict[str, Any]]:
        """
        Estimates savings from removing an orphaned snapshot with no active parent volume.
        """
        cost = resource.monthly_cost or Decimal("0.0000")
        if cost > Decimal("0.0000"):
            return cost, "100% of orphaned snapshot recurring monthly charge", {"source": "resource.monthly_cost"}

        if billing_records:
            total = sum((b.unblended_cost for b in billing_records), Decimal("0.0000"))
            if total > Decimal("0.0000"):
                return total, "Sum of historical snapshot tier usage charges", {"source": "billing_records_sum"}

        return Decimal("0.0000"), "Snapshot storage charges not isolated in billing ledger", {"source": "NONE"}
