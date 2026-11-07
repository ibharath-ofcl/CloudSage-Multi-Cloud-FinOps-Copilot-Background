"""
CloudSage Root-Cause Attribution Engine.
Analyzes underlying billing records and correlates with Stage 5 CloudResource inventory
to identify top contributing resources, SKUs, and regions, producing factual FinOps explanations.
"""

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.anomaly_detection.models import AnomalyCandidate
from backend.app.anomaly_detection.statistics import PRECISION_FOUR
from backend.app.models.billing import BillingRecord
from backend.app.models.resource import CloudResource


def generate_attribution_narrative(
    candidate: AnomalyCandidate,
    top_resource: Optional[Dict[str, Any]],
    top_sku: Optional[Dict[str, Any]],
    is_unknown: bool = False,
) -> str:
    """Generates a factual, non-hallucinatory narrative explaining the cost anomaly."""
    provider = candidate.provider
    service = candidate.service_name or "Cloud Infrastructure"
    date_str = candidate.anomaly_date.isoformat()
    obs_cost = f"${candidate.observed_cost:,.2f}"
    exp_cost = f"${candidate.expected_cost:,.2f}"
    excess_cost = f"${candidate.estimated_excess_cost:,.2f}"
    pct_str = f"{candidate.percentage_deviation:,.1f}%"

    if is_unknown or (not top_resource and not top_sku):
        return (
            f"On {date_str}, {provider} {service} daily expenditure reached {obs_cost}, "
            f"representing a {pct_str} increase over the expected baseline of {exp_cost} "
            f"(excess cost: {excess_cost}). "
            f"Root cause inconclusive across individual resources; spend was distributed across "
            f"multiple resources or SKUs without a dominant single contributor."
        )

    narrative_parts = [
        f"On {date_str}, {provider} {service} daily expenditure reached {obs_cost}, "
        f"increasing {pct_str} above the expected baseline of {exp_cost} "
        f"(excess spend of {excess_cost})."
    ]

    if top_resource:
        res_id = top_resource.get("resource_id", "Unknown")
        res_name = top_resource.get("resource_name") or res_id
        res_share = top_resource.get("share_percentage", Decimal("0.0"))
        res_cost = top_resource.get("cost", Decimal("0.0"))
        owner = top_resource.get("owner") or "Unassigned"
        env = top_resource.get("environment") or "unknown"
        narrative_parts.append(
            f"Primary contributing resource was '{res_name}' ({res_id}) in '{env}' environment "
            f"(owner: {owner}), accounting for {res_share:.1f}% (${res_cost:,.2f}) of anomalous spend."
        )

    if top_sku:
        sku_id = top_sku.get("sku_id", "Unknown")
        sku_share = top_sku.get("share_percentage", Decimal("0.0"))
        sku_cost = top_sku.get("cost", Decimal("0.0"))
        narrative_parts.append(
            f"Dominant SKU was '{sku_id}' contributing {sku_share:.1f}% (${sku_cost:,.2f}) of expenditure."
        )

    narrative_parts.append(
        "FinOps recommendation: Inspect recent deployment logs, auto-scaling configurations, "
        "and provisioned capacity allocations for the identified resource and service."
    )

    return " ".join(narrative_parts)


def attribute_anomaly(
    db: Session,
    candidate: AnomalyCandidate,
) -> AnomalyCandidate:
    """
    Correlates an anomaly candidate with underlying billing records and resource inventory.
    Enriches candidate with ranked contributors, inventory metadata, and narrative explanation.
    """
    dt_start = datetime.combine(candidate.anomaly_date, time.min, tzinfo=timezone.utc)
    dt_end = dt_start + timedelta(days=1)

    # Query billing records for this date and dimension
    query = db.query(BillingRecord).filter(
        BillingRecord.provider == candidate.provider,
        BillingRecord.usage_start_time >= dt_start,
        BillingRecord.usage_start_time < dt_end,
    )

    if candidate.account_id:
        query = query.filter(BillingRecord.subscription_id == candidate.account_id)
    if candidate.service_name:
        query = query.filter(BillingRecord.service_name == candidate.service_name)
    if candidate.region:
        query = query.filter(BillingRecord.region == candidate.region)

    records: List[BillingRecord] = query.all()

    if not records:
        # Fallback if specific filtered records aren't found or already pre-aggregated
        candidate.root_cause_analysis = {
            "status": "ROOT_CAUSE_UNKNOWN",
            "reason": "NO_UNDERLYING_BILLING_RECORDS_FOUND",
            "evaluated_date": candidate.anomaly_date.isoformat(),
        }
        candidate.explanation = generate_attribution_narrative(candidate, None, None, is_unknown=True)
        if not candidate.title:
            candidate.title = f"Cost Anomaly on {candidate.provider} {candidate.service_name or 'Spend'}"
        return candidate

    # Aggregate by resource and SKU
    resource_costs: Dict[str, Decimal] = defaultdict(lambda: Decimal("0.0000"))
    sku_costs: Dict[str, Decimal] = defaultdict(lambda: Decimal("0.0000"))
    region_costs: Dict[str, Decimal] = defaultdict(lambda: Decimal("0.0000"))
    billing_refs: List[str] = []

    total_cost = Decimal("0.0000")
    for rec in records:
        cost = rec.unblended_cost or rec.blended_cost or Decimal("0.0000")
        if cost > Decimal("0.0000"):
            total_cost += cost
            r_id = rec.resource_id or "UNALLOCATED_RESOURCE"
            s_id = (
                rec.pricing_model.value
                if hasattr(rec.pricing_model, 'value')
                else str(rec.pricing_model or "STANDARD_SKU")
            )
            reg = rec.region or "GLOBAL"
            resource_costs[r_id] += cost
            sku_costs[s_id] += cost
            region_costs[reg] += cost
            billing_refs.append(str(rec.record_id))

    candidate.source_billing_references = billing_refs[:100]

    # Calculate percentages and rank resources
    top_resources: List[Dict[str, Any]] = []
    for res_id, cost in sorted(resource_costs.items(), key=lambda item: item[1], reverse=True)[:10]:
        share_pct = (
            ((cost / total_cost) * Decimal("100.0000")).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)
            if total_cost > Decimal("0.0000")
            else Decimal("0.0000")
        )

        res_meta: Dict[str, Any] = {
            "resource_id": res_id,
            "cost": cost.quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP),
            "share_percentage": share_pct,
            "resource_name": None,
            "resource_type": None,
            "owner": None,
            "environment": None,
            "project": None,
            "cost_center": None,
            "status": None,
        }

        # Correlate with Stage 5 CloudResource inventory
        if res_id != "UNALLOCATED_RESOURCE":
            inv_res = db.query(CloudResource).filter(
                CloudResource.resource_id == res_id,
                CloudResource.provider == candidate.provider,
            ).first()
            if inv_res:
                res_meta.update({
                    "resource_name": inv_res.resource_name,
                    "resource_type": inv_res.resource_type,
                    "owner": inv_res.owner,
                    "environment": inv_res.environment,
                    "project": inv_res.project,
                    "cost_center": inv_res.cost_center,
                    "status": inv_res.status,
                })

        top_resources.append(res_meta)

    # Rank SKUs
    top_skus: List[Dict[str, Any]] = []
    for s_id, cost in sorted(sku_costs.items(), key=lambda item: item[1], reverse=True)[:5]:
        share_pct = (
            ((cost / total_cost) * Decimal("100.0000")).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)
            if total_cost > Decimal("0.0000")
            else Decimal("0.0000")
        )
        top_skus.append({
            "sku_id": s_id,
            "cost": cost.quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP),
            "share_percentage": share_pct,
        })

    candidate.contributing_resources = top_resources

    primary_res = top_resources[0] if top_resources else None
    primary_sku = top_skus[0] if top_skus else None

    # Check if primary contributor is dominant (>= 20%)
    is_unknown = False
    if primary_res and primary_res["share_percentage"] < Decimal("20.0000"):
        is_unknown = True

    candidate.root_cause_analysis = {
        "status": "ATTRIBUTED" if not is_unknown else "ROOT_CAUSE_UNKNOWN",
        "primary_contributor_type": "RESOURCE" if (primary_res and not is_unknown) else "DISTRIBUTED",
        "total_evaluated_cost": total_cost.quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP),
        "top_resource": primary_res,
        "top_sku": primary_sku,
        "sku_breakdown": top_skus,
        "region_breakdown": [
            {"region": r, "cost": str(c.quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP))}
            for r, c in region_costs.items()
        ],
    }

    candidate.explanation = generate_attribution_narrative(candidate, primary_res, primary_sku, is_unknown=is_unknown)
    if not candidate.title:
        target_name = candidate.service_name or candidate.provider
        candidate.title = f"Unusual Spend Surge in {candidate.provider} {target_name}"

    return candidate
