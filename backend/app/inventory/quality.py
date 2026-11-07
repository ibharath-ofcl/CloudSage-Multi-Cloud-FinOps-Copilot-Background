"""
CloudSage Inventory Quality Evaluator.
Assesses completeness, metadata integrity, tag governance, and lifecycle hygiene
across multi-cloud resource inventories. Generates structured findings and persists
auditable InventoryQualityReport snapshots.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.models.inventory import InventoryQualityReport
from backend.app.models.resource import CloudResource


class InventoryQualityEvaluator:
    """Evaluates inventory health, tag coverage, and data completeness."""

    @classmethod
    def evaluate(
        cls,
        db: Session,
        provider: Optional[str] = None,
        sync_run_id: Optional[uuid.UUID] = None,
        persist: bool = True,
    ) -> InventoryQualityReport:
        """
        Runs comprehensive inventory audit, generates severity-tiered findings,
        computes composite confidence metrics, and optionally persists report.
        """
        now = datetime.now(timezone.utc)
        query = db.query(CloudResource)
        if provider:
            query = query.filter(CloudResource.provider == provider.upper())

        resources: List[CloudResource] = query.all()
        total_count = len(resources)

        if total_count == 0:
            report = InventoryQualityReport(
                sync_run_id=sync_run_id,
                provider=provider.upper() if provider else "ALL",
                total_resources=0,
                completeness_score=Decimal("100.00"),
                tag_completeness_score=Decimal("100.00"),
                inventory_confidence=Decimal("1.0000"),
                findings_count=0,
                critical_findings=0,
                high_findings=0,
                medium_findings=0,
                low_findings=0,
                findings_summary={"categories": {}, "issues": []},
            )
            if persist:
                db.add(report)
                db.commit()
            return report

        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0
        issues = []

        total_attr_checks = total_count * 5  # owner, env, project/dept, region, status
        passed_attr_checks = 0
        total_tag_scores = Decimal("0.00")

        stale_cutoff = now - timedelta(days=14)

        for res in resources:
            total_tag_scores += res.tag_quality_score or Decimal("0.00")

            # Check 1: Owner
            if res.owner and res.owner.strip() != "":
                passed_attr_checks += 1
            else:
                critical_count += 1
                if len(issues) < 20:
                    issues.append({
                        "resource_id": res.resource_id,
                        "severity": "CRITICAL",
                        "rule": "MISSING_OWNER",
                        "message": "Resource lacks mandatory owner tag or identity metadata",
                    })

            # Check 2: Environment
            if res.environment and res.environment not in ("unknown", ""):
                passed_attr_checks += 1
            else:
                high_count += 1
                if len(issues) < 20:
                    issues.append({
                        "resource_id": res.resource_id,
                        "severity": "HIGH",
                        "rule": "MISSING_ENVIRONMENT",
                        "message": "Resource environment tag is unassigned or set to 'unknown'",
                    })

            # Check 3: Project / Cost Center
            if (res.project and res.project.strip()) or (res.cost_center and res.cost_center.strip()):
                passed_attr_checks += 1
            else:
                medium_count += 1
                if len(issues) < 20:
                    issues.append({
                        "resource_id": res.resource_id,
                        "severity": "MEDIUM",
                        "rule": "MISSING_COST_ALLOCATION",
                        "message": "Resource lacks both project and cost_center allocation tags",
                    })

            # Check 4: Region
            if res.region and res.region.strip() != "":
                passed_attr_checks += 1
            else:
                low_count += 1

            # Check 5: Status
            if res.status and res.status != "unknown":
                passed_attr_checks += 1
            else:
                low_count += 1

            # Check Freshness / Stale
            last_sync = res.last_inventory_sync_at
            if last_sync and last_sync.tzinfo is None:
                last_sync = last_sync.replace(tzinfo=timezone.utc)

            if res.discovery_status == "STALE" or (last_sync and last_sync < stale_cutoff):
                high_count += 1
                if len(issues) < 20:
                    issues.append({
                        "resource_id": res.resource_id,
                        "severity": "HIGH",
                        "rule": "STALE_RESOURCE",
                        "message": "Resource has not been confirmed in discovery for over 14 days",
                    })

        # Calculations
        completeness_pct = (Decimal(str(passed_attr_checks)) / Decimal(str(total_attr_checks)) * Decimal("100.00")).quantize(Decimal("0.01"))
        avg_tag_quality = (total_tag_scores / Decimal(str(total_count))).quantize(Decimal("0.01"))

        # Inventory confidence composite: 0.4 * completeness + 0.4 * tag_quality + 0.2 * freshness
        stale_ratio = Decimal(str(high_count)) / Decimal(str(total_count)) if total_count > 0 else Decimal("0.0")
        freshness_score = max(Decimal("0.00"), Decimal("100.00") - (stale_ratio * Decimal("50.00")))
        composite_score = (
            (completeness_pct * Decimal("0.40"))
            + (avg_tag_quality * Decimal("0.40"))
            + (freshness_score * Decimal("0.20"))
        ) / Decimal("100.00")
        inventory_confidence = min(Decimal("1.0000"), max(Decimal("0.0000"), composite_score.quantize(Decimal("0.0001"))))

        findings_count = critical_count + high_count + medium_count + low_count

        report = InventoryQualityReport(
            sync_run_id=sync_run_id,
            provider=provider.upper() if provider else "ALL",
            total_resources=total_count,
            completeness_score=completeness_pct,
            tag_completeness_score=avg_tag_quality,
            inventory_confidence=inventory_confidence,
            findings_count=findings_count,
            critical_findings=critical_count,
            high_findings=high_count,
            medium_findings=medium_count,
            low_findings=low_count,
            findings_summary={
                "evaluated_at": now.isoformat(),
                "total_resources": total_count,
                "freshness_score": float(freshness_score),
                "sample_issues": issues,
            },
        )

        if persist:
            db.add(report)
            db.commit()

        return report
