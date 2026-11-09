"""
CloudSage Enterprise Observability & Production Telemetry.
Provides structured JSON logging, Prometheus metrics instrumentation,
request correlation tracking (X-Request-ID), and dependency health diagnostics.
"""

import json
import logging
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    REGISTRY,
    generate_latest,
)

# ContextVar for request-scoped correlation ID
request_id_ctx_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_current_request_id() -> str:
    """Returns the current request correlation ID or generates an ephemeral one."""
    req_id = request_id_ctx_var.get()
    return req_id or f"ephemeral-{uuid.uuid4().hex[:8]}"


class JSONLogFormatter(logging.Formatter):
    """Structured JSON formatter for production log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx_var.get() or "-",
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            log_obj["status_code"] = record.status_code
        if hasattr(record, "client_ip"):
            log_obj["client_ip"] = record.client_ip
        if hasattr(record, "http_method"):
            log_obj["method"] = record.http_method
        if hasattr(record, "path"):
            log_obj["path"] = record.path
        return json.dumps(log_obj)


def setup_structured_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configures root logger with structured JSON formatting for production."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to prevent duplicate lines
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler()
    if log_format.lower() == "json":
        stream_handler.setFormatter(JSONLogFormatter())
    else:
        stream_handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
        )
    root_logger.addHandler(stream_handler)


# Prometheus Metric Collectors
REQUEST_COUNT = Counter(
    "cloudsage_http_requests_total",
    "Total count of HTTP requests handled by CloudSage backend",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "cloudsage_http_request_duration_seconds",
    "HTTP request latency in seconds across endpoints",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

ACTIVE_REQUESTS = Gauge(
    "cloudsage_active_requests",
    "Number of currently active in-flight HTTP requests",
)

FINOPS_ANOMALIES_TOTAL = Counter(
    "cloudsage_finops_anomalies_detected_total",
    "Total FinOps cost anomalies detected by the anomaly engine",
    ["cloud_provider", "severity"],
)

FINOPS_RECOMMENDATIONS_ACTIVE = Gauge(
    "cloudsage_finops_recommendations_active",
    "Total active FinOps recommendations available for review",
    ["category"],
)

FINOPS_POTENTIAL_SAVINGS_USD = Gauge(
    "cloudsage_finops_potential_savings_usd",
    "Total identified monthly potential savings in USD",
    ["category"],
)


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """
    Middleware injecting X-Request-ID correlation headers, tracking Prometheus
    request metrics, and emitting structured JSON access logs.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract or generate X-Request-ID
        req_id = request.headers.get("X-Request-ID")
        if not req_id or not req_id.strip():
            req_id = str(uuid.uuid4())
        
        token = request_id_ctx_var.set(req_id)
        ACTIVE_REQUESTS.inc()
        start_time = time.perf_counter()

        endpoint_path = request.url.path
        method = request.method
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = req_id
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start_time
            ACTIVE_REQUESTS.dec()
            REQUEST_COUNT.labels(method=method, endpoint=endpoint_path, status_code=str(status_code)).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint_path).observe(duration)
            request_id_ctx_var.reset(token)

            # Emit structured request log
            logger = logging.getLogger("cloudsage.access")
            client_ip = request.client.host if request.client else "unknown"
            extra = {
                "duration_ms": round(duration * 1000, 2),
                "status_code": status_code,
                "client_ip": client_ip,
                "http_method": method,
                "path": endpoint_path,
            }
            logger.info(
                f"{method} {endpoint_path} {status_code} ({extra['duration_ms']}ms)",
                extra=extra,
            )


def get_prometheus_metrics() -> str:
    """Generates the latest Prometheus metrics in standard exposition format."""
    return generate_latest(REGISTRY).decode("utf-8")


def check_dependency_health(db_session=None) -> Dict[str, Any]:
    """
    Evaluates deep dependency health including database connectivity,
    cache/redis subsystem, and filesystem storage permissions.
    """
    start_time = time.perf_counter()
    dependencies: Dict[str, Any] = {}
    overall_status = "healthy"

    # 1. Database Check
    db_start = time.perf_counter()
    try:
        from backend.app.core.database import SessionLocal
        from sqlalchemy import text
        session = db_session or SessionLocal()
        try:
            session.execute(text("SELECT 1"))
            db_latency = round((time.perf_counter() - db_start) * 1000, 2)
            dependencies["database"] = {
                "status": "healthy",
                "latency_ms": db_latency,
                "type": "relational_postgresql_compatible",
            }
        finally:
            if not db_session:
                session.close()
    except Exception as exc:
        overall_status = "unhealthy"
        dependencies["database"] = {
            "status": "unhealthy",
            "error": str(exc),
            "latency_ms": round((time.perf_counter() - db_start) * 1000, 2),
        }

    # 2. Cache / Redis Subsystem
    from backend.app.core.config import settings
    redis_start = time.perf_counter()
    if settings.NOTIFICATION_SAFE_LOCAL_MODE:
        dependencies["cache_broker"] = {
            "status": "healthy",
            "mode": "in_memory_safe_local_mode",
            "latency_ms": round((time.perf_counter() - redis_start) * 1000, 2),
        }
    else:
        try:
            import redis
            r = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                socket_timeout=settings.HEALTHCHECK_TIMEOUT_SECONDS,
            )
            r.ping()
            dependencies["cache_broker"] = {
                "status": "healthy",
                "mode": "redis",
                "latency_ms": round((time.perf_counter() - redis_start) * 1000, 2),
            }
        except Exception as exc:
            # Non-critical fallback if in dev or degraded
            if overall_status == "healthy":
                overall_status = "degraded"
            dependencies["cache_broker"] = {
                "status": "degraded",
                "error": str(exc),
                "mode": "redis_unreachable",
                "latency_ms": round((time.perf_counter() - redis_start) * 1000, 2),
            }

    # 3. Storage / Filesystem Permissions
    fs_start = time.perf_counter()
    try:
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(prefix="cloudsage_health_", delete=True) as tf:
            tf.write(b"healthcheck_ok")
            tf.flush()
        dependencies["storage"] = {
            "status": "healthy",
            "latency_ms": round((time.perf_counter() - fs_start) * 1000, 2),
            "writable": True,
        }
    except Exception as exc:
        if overall_status == "healthy":
            overall_status = "degraded"
        dependencies["storage"] = {
            "status": "unhealthy",
            "error": str(exc),
            "writable": False,
        }

    total_latency = round((time.perf_counter() - start_time) * 1000, 2)
    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_latency_ms": total_latency,
        "dependencies": dependencies,
    }

