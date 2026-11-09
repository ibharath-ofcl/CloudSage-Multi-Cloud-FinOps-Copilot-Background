"""
CloudSage Backend FastAPI Application.
Initializes REST API routes, middleware, OpenAPI documentation, and health endpoints.
"""

from fastapi import FastAPI, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, PlainTextResponse
from backend.app.api.routes import (
    alerts,
    anomaly_detection,
    auth,
    copilot,
    dashboard,
    ingestion,
    inventory,
    investigations,
    normalization,
    recommendations,
    roles,
    security,
    users,
    waste_detection,
)
from backend.app.core.config import settings
from backend.app.core.observability import (
    RequestCorrelationMiddleware,
    check_dependency_health,
    get_prometheus_metrics,
    setup_structured_logging,
)

# Initialize structured JSON logging
setup_structured_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Multi-Cloud FinOps Copilot Platform Backend API.",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Request Correlation & Observability Middleware
app.add_middleware(RequestCorrelationMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Sub-Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(roles.router, prefix=settings.API_V1_STR)
app.include_router(security.router, prefix=settings.API_V1_STR)
app.include_router(ingestion.router, prefix=settings.API_V1_STR)
app.include_router(normalization.router, prefix=settings.API_V1_STR)
app.include_router(inventory.router, prefix=settings.API_V1_STR)
app.include_router(waste_detection.router, prefix=settings.API_V1_STR)
app.include_router(anomaly_detection.router, prefix=settings.API_V1_STR)
app.include_router(recommendations.router, prefix=settings.API_V1_STR)
app.include_router(copilot.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(alerts.router, prefix=settings.API_V1_STR)
app.include_router(investigations.router, prefix=settings.API_V1_STR)


@app.get("/dashboard", tags=["FinOps Dashboards & Visualizations"], include_in_schema=False)
def dashboard_ui_redirect():
    """Redirect top-level /dashboard path to the interactive HTML5 FinOps dashboard."""
    return RedirectResponse(url=f"{settings.API_V1_STR}/dashboard/ui")


@app.get("/", tags=["Root"])
def root():
    return {
        "project": settings.PROJECT_NAME,
        "status": "online",
        "version": settings.VERSION,
        "documentation": "/docs",
        "dashboard": "/dashboard",
    }


@app.get("/health/liveness", tags=["Health"])
def liveness_probe():
    """Liveness probe confirming service process is active."""
    return {
        "status": "healthy",
        "service": "cloudsage-backend",
        "version": settings.VERSION,
    }


@app.get("/health/readiness", tags=["Health"])
def readiness_probe():
    """Readiness probe confirming database and core dependency readiness."""
    health = check_dependency_health()
    is_ready = health["status"] in ("healthy", "degraded")
    return {
        "status": "ready" if is_ready else "unready",
        "database": health["dependencies"].get("database", {}).get("status", "unknown"),
        "version": settings.VERSION,
    }


@app.get("/health/dependencies", tags=["Health"])
def dependency_health_probe():
    """Deep dependency health check for DB, cache, and filesystem storage."""
    return check_dependency_health()


@app.get("/metrics", tags=["Observability"], response_class=PlainTextResponse)
def prometheus_metrics():
    """Exposes Prometheus exposition format metrics for scrapers."""
    return PlainTextResponse(get_prometheus_metrics(), media_type="text/plain; version=0.0.4; charset=utf-8")
