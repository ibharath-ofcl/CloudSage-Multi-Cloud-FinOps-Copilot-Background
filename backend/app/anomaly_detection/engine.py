"""
CloudSage Cost Anomaly Detection Engine.
Orchestrates multi-cloud time-series aggregation, statistical baseline computation,
detector execution, attribution correlation, and lifecycle state management.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.anomaly_detection.aggregation import aggregate_time_series
from backend.app.anomaly_detection.attribution import attribute_anomaly
from backend.app.anomaly_detection.baseline import calculate_baseline, persist_baseline
from backend.app.anomaly_detection.impact import aggregate_deduplicated_impact
from backend.app.anomaly_detection.lifecycle import persist_or_update_anomaly
from backend.app.anomaly_detection.models import AnomalyCandidate
from backend.app.anomaly_detection.registry import get_detector_registry
from backend.app.core.enums import AnomalyCategory, AnomalyStatus, Severity
from backend.app.models.anomaly import AnomalyDetectionRun, CostAnomaly, CostBaseline


class AnomalyDetectionEngine:
    """Enterprise multi-cloud cost anomaly detection engine."""

    def __init__(self) -> None:
        self.registry = get_detector_registry()

    def execute_detection_run(
        self,
        db: Session,
        provider: Optional[str] = None,
        account_id: Optional[str] = None,
        service_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        baseline_window_days: int = 30,
        detector_ids: Optional[List[str]] = None,
        scope: str = "FULL",
    ) -> AnomalyDetectionRun:
        """
        Executes a complete anomaly detection run across aggregated time-series.
        Extracts series, computes baselines, runs detectors, correlates attribution,
        and saves findings to PostgreSQL.
        """
        run_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        effective_provider = provider or "ALL"

        run_record = AnomalyDetectionRun(
            run_id=run_id,
            provider=effective_provider,
            scope=scope,
            status="RUNNING",
            started_at=now,
            detector_summary={},
            error_details=[],
        )
        db.add(run_record)
        db.flush()

        # Date defaults: trailing window up to yesterday/today
        if not end_date:
            end_date = now.date()
        if not start_date:
            start_date = end_date - timedelta(days=baseline_window_days + 14)

        total_series = 0
        baselines_gen = 0
        created_count = 0
        updated_count = 0
        reopened_count = 0
        resolved_count = 0
        unchanged_count = 0
        detector_stats: Dict[str, int] = {}
        all_candidates: List[AnomalyCandidate] = []
        errors: List[str] = []

        # Dimensions to scan: SERVICE, RESOURCE, PROVIDER, ACCOUNT
        dims_to_evaluate = ["SERVICE", "RESOURCE", "PROVIDER"]
        if account_id:
            dims_to_evaluate.append("ACCOUNT")

        try:
            for dim in dims_to_evaluate:
                series_list = aggregate_time_series(
                    db=db,
                    dimension_type=dim,
                    provider=provider,
                    account_id=account_id,
                    service_name=service_name,
                    start_date=start_date,
                    end_date=end_date,
                )

                for ts in series_list:
                    total_series += 1
                    base_res = calculate_baseline(ts, window_days=baseline_window_days)

                    if base_res.status != "INSUFFICIENT_HISTORY":
                        persist_baseline(db, ts, base_res)
                        baselines_gen += 1

                    # Get applicable detectors
                    if detector_ids:
                        detectors = [self.registry.get(did) for did in detector_ids if self.registry.get(did)]
                        detectors = [d for d in detectors if d and dim in d.supported_dimensions]
                    else:
                        detectors = self.registry.get_for_dimension(dim)

                    for detector in detectors:
                        try:
                            exec_res = detector.detect(
                                time_series=ts,
                                baseline=base_res,
                            )
                            if exec_res.status == "DETECTED":
                                for cand in exec_res.anomalies:
                                    # Attributing underlying billing & inventory
                                    attr_cand = attribute_anomaly(db, cand)
                                    all_candidates.append(attr_cand)

                                    # Persisting or updating
                                    res = persist_or_update_anomaly(db, attr_cand)
                                    action = res["action"]
                                    if action == "created":
                                        created_count += 1
                                    elif action == "updated":
                                        updated_count += 1
                                    elif action == "reopened":
                                        reopened_count += 1
                                    else:
                                        unchanged_count += 1

                                    detector_stats[detector.detector_id] = (
                                        detector_stats.get(detector.detector_id, 0) + 1
                                    )
                        except Exception as e:
                            errors.append(f"Detector {detector.detector_id} failed on series {ts.dimension_key}: {str(e)}")

            # Calculate anti-double-counting aggregate excess cost
            impact_dicts = [
                {
                    "provider": c.provider,
                    "account_id": c.account_id,
                    "service_name": c.service_name,
                    "anomaly_date": c.anomaly_date,
                    "resource_id": c.resource_id,
                    "estimated_excess_cost": c.estimated_excess_cost,
                }
                for c in all_candidates
            ]
            agg_impact = aggregate_deduplicated_impact(impact_dicts)
            total_excess = agg_impact["deduplicated_total_excess_cost"]

            # Finalize run audit record
            run_record.status = "COMPLETED" if not errors else "PARTIAL_SUCCESS"
            run_record.completed_at = datetime.now(timezone.utc)
            run_record.total_series_evaluated = total_series
            run_record.baselines_generated = baselines_gen
            run_record.anomalies_created = created_count
            run_record.anomalies_updated = updated_count
            run_record.anomalies_unchanged = unchanged_count
            run_record.anomalies_resolved = resolved_count
            run_record.total_excess_cost = total_excess
            run_record.detector_summary = detector_stats
            run_record.error_details = errors

            db.commit()
            db.refresh(run_record)
            return run_record

        except Exception as e:
            db.rollback()
            run_record.status = "FAILED"
            run_record.completed_at = datetime.now(timezone.utc)
            run_record.error_details = errors + [str(e)]
            db.add(run_record)
            db.commit()
            db.refresh(run_record)
            raise e

    def list_anomalies(
        self,
        db: Session,
        provider: Optional[str] = None,
        account_id: Optional[str] = None,
        service_name: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CostAnomaly]:
        """Queries and filters CostAnomaly records with pagination."""
        query = db.query(CostAnomaly)

        if provider:
            query = query.filter(CostAnomaly.provider == provider)
        if account_id:
            query = query.filter(CostAnomaly.account_id == account_id)
        if service_name:
            query = query.filter(CostAnomaly.service_name == service_name)
        if status:
            query = query.filter(CostAnomaly.status == status)
        if severity:
            query = query.filter(CostAnomaly.severity == severity)
        if category:
            query = query.filter(CostAnomaly.anomaly_category == category)
        if start_date:
            query = query.filter(CostAnomaly.anomaly_date >= start_date)
        if end_date:
            query = query.filter(CostAnomaly.anomaly_date <= end_date)

        return query.order_by(CostAnomaly.anomaly_date.desc(), CostAnomaly.estimated_excess_cost.desc()).offset(offset).limit(limit).all()

    def count_anomalies(
        self,
        db: Session,
        provider: Optional[str] = None,
        account_id: Optional[str] = None,
        service_name: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> int:
        """Returns total count of matching CostAnomaly records."""
        query = db.query(func.count(CostAnomaly.id))

        if provider:
            query = query.filter(CostAnomaly.provider == provider)
        if account_id:
            query = query.filter(CostAnomaly.account_id == account_id)
        if service_name:
            query = query.filter(CostAnomaly.service_name == service_name)
        if status:
            query = query.filter(CostAnomaly.status == status)
        if severity:
            query = query.filter(CostAnomaly.severity == severity)
        if category:
            query = query.filter(CostAnomaly.anomaly_category == category)
        if start_date:
            query = query.filter(CostAnomaly.anomaly_date >= start_date)
        if end_date:
            query = query.filter(CostAnomaly.anomaly_date <= end_date)

        return query.scalar() or 0

    def get_anomaly_by_id(self, db: Session, anomaly_id: Any) -> Optional[CostAnomaly]:
        """Retrieves a single CostAnomaly by primary key."""
        target_id = anomaly_id
        if isinstance(anomaly_id, str):
            try:
                target_id = uuid.UUID(anomaly_id)
            except Exception:
                target_id = anomaly_id
        return db.query(CostAnomaly).filter(CostAnomaly.id == target_id).first()

    def get_summary(
        self,
        db: Session,
        provider: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Aggregates high-level FinOps anomaly statistics."""
        query = db.query(CostAnomaly)
        if provider:
            query = query.filter(CostAnomaly.provider == provider)
        if account_id:
            query = query.filter(CostAnomaly.account_id == account_id)

        anomalies = query.all()
        total_count = len(anomalies)

        by_severity: Dict[str, int] = {s.value: 0 for s in Severity}
        by_status: Dict[str, int] = {s.value: 0 for s in AnomalyStatus}
        by_category: Dict[str, int] = {c.value: 0 for c in AnomalyCategory}

        total_excess = Decimal("0.0000")
        total_monthly = Decimal("0.0000")
        active_count = 0

        for a in anomalies:
            sev = a.severity or Severity.MEDIUM.value
            stat = a.status or AnomalyStatus.DETECTED.value
            cat = a.anomaly_category or AnomalyCategory.SERVICE_SPIKE.value

            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_status[stat] = by_status.get(stat, 0) + 1
            by_category[cat] = by_category.get(cat, 0) + 1

            total_excess += a.estimated_excess_cost or Decimal("0.0000")
            total_monthly += a.projected_monthly_impact or Decimal("0.0000")

            if stat in (AnomalyStatus.DETECTED.value, AnomalyStatus.INVESTIGATING.value, AnomalyStatus.ACKNOWLEDGED.value, AnomalyStatus.REOPENED.value, "OPEN"):
                active_count += 1

        return {
            "total_anomalies": total_count,
            "active_anomalies": active_count,
            "by_severity": by_severity,
            "by_status": by_status,
            "by_category": by_category,
            "total_excess_cost": total_excess,
            "total_projected_monthly_impact": total_monthly,
            "currency": "USD",
        }

    def get_trend(
        self,
        db: Session,
        anomaly_id: Any,
        days_before: int = 14,
        days_after: int = 7,
    ) -> Optional[Dict[str, Any]]:
        """Returns contiguous expenditure trend points around the anomaly date."""
        anomaly = self.get_anomaly_by_id(db, anomaly_id)
        if not anomaly:
            return None

        start_dt = anomaly.anomaly_date - timedelta(days=days_before)
        end_dt = anomaly.anomaly_date + timedelta(days=days_after)

        dim = "RESOURCE" if anomaly.resource_id else "SERVICE"
        series_list = aggregate_time_series(
            db=db,
            dimension_type=dim,
            provider=anomaly.provider,
            account_id=anomaly.account_id,
            service_name=anomaly.service_name,
            start_date=start_dt,
            end_date=end_dt,
        )

        target_series = None
        for s in series_list:
            if anomaly.resource_id and s.resource_id == anomaly.resource_id:
                target_series = s
                break
            elif not anomaly.resource_id and s.service_name == anomaly.service_name:
                target_series = s
                break

        if not target_series and series_list:
            target_series = series_list[0]

        points = []
        if target_series:
            for pt in target_series.points:
                points.append({
                    "date": pt.point_date,
                    "cost": pt.cost,
                    "is_anomaly_date": (pt.point_date == anomaly.anomaly_date),
                })

        baseline_mean = anomaly.expected_cost or Decimal("0.0000")
        upper_fence = baseline_mean + (anomaly.absolute_deviation or Decimal("0.0000"))

        return {
            "anomaly_id": str(anomaly.id),
            "dimension": dim,
            "dimension_key": anomaly.resource_id or anomaly.service_name or anomaly.provider,
            "baseline_mean": baseline_mean,
            "upper_fence": upper_fence,
            "points": points,
        }

    def get_contributors(self, db: Session, anomaly_id: Any) -> Optional[Dict[str, Any]]:
        """Returns top resource and SKU contributors for an anomaly."""
        anomaly = self.get_anomaly_by_id(db, anomaly_id)
        if not anomaly:
            return None

        return {
            "anomaly_id": str(anomaly.id),
            "root_cause_analysis": anomaly.root_cause_analysis or {},
            "contributing_resources": anomaly.contributing_resources or [],
        }

    def list_baselines(
        self,
        db: Session,
        provider: Optional[str] = None,
        service_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CostBaseline]:
        """Queries computed cost baselines."""
        query = db.query(CostBaseline)
        if provider:
            query = query.filter(CostBaseline.provider == provider)
        if service_name:
            query = query.filter(CostBaseline.service_name == service_name)
        return query.order_by(CostBaseline.calculated_at.desc()).offset(offset).limit(limit).all()

    def get_baseline_by_id(self, db: Session, baseline_id: Any) -> Optional[CostBaseline]:
        """Retrieves a single CostBaseline by ID."""
        target_id = baseline_id
        if isinstance(baseline_id, str):
            try:
                target_id = uuid.UUID(baseline_id)
            except Exception:
                target_id = baseline_id
        return db.query(CostBaseline).filter(CostBaseline.id == target_id).first()

    def list_runs(self, db: Session, limit: int = 20, offset: int = 0) -> List[AnomalyDetectionRun]:
        """Queries historical anomaly detection run audit logs."""
        return db.query(AnomalyDetectionRun).order_by(AnomalyDetectionRun.started_at.desc()).offset(offset).limit(limit).all()

    def get_run_by_id(self, db: Session, run_id: uuid.UUID) -> Optional[AnomalyDetectionRun]:
        """Retrieves an anomaly detection run by UUID."""
        return db.query(AnomalyDetectionRun).filter(AnomalyDetectionRun.run_id == run_id).first()
