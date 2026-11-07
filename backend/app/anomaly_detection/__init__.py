"""
CloudSage Intelligent Multi-Cloud Cost Anomaly Detection Engine.
"""

from backend.app.anomaly_detection.aggregation import aggregate_time_series
from backend.app.anomaly_detection.attribution import attribute_anomaly
from backend.app.anomaly_detection.base import BaseAnomalyDetector
from backend.app.anomaly_detection.baseline import calculate_baseline, persist_baseline
from backend.app.anomaly_detection.change_points import detect_change_points
from backend.app.anomaly_detection.engine import AnomalyDetectionEngine
from backend.app.anomaly_detection.impact import (
    calculate_deviations,
    calculate_excess_cost,
    calculate_projected_impact,
    determine_severity,
)
from backend.app.anomaly_detection.lifecycle import (
    check_and_auto_resolve,
    persist_or_update_anomaly,
    update_anomaly_status,
)
from backend.app.anomaly_detection.models import (
    AnomalyCandidate,
    BaselineResult,
    ChangePointResult,
    DetectorExecutionResult,
    TimeSeries,
    TimeSeriesPoint,
)
from backend.app.anomaly_detection.registry import (
    AnomalyDetectorRegistry,
    get_detector_registry,
)

__all__ = [
    "AnomalyDetectionEngine",
    "BaseAnomalyDetector",
    "AnomalyDetectorRegistry",
    "get_detector_registry",
    "calculate_baseline",
    "persist_baseline",
    "detect_change_points",
    "aggregate_time_series",
    "attribute_anomaly",
    "persist_or_update_anomaly",
    "check_and_auto_resolve",
    "update_anomaly_status",
    "calculate_deviations",
    "calculate_excess_cost",
    "calculate_projected_impact",
    "determine_severity",
    "TimeSeriesPoint",
    "TimeSeries",
    "BaselineResult",
    "AnomalyCandidate",
    "ChangePointResult",
    "DetectorExecutionResult",
]

