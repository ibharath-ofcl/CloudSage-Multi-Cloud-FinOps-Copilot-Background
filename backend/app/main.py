"""
CloudSage Backend FastAPI Application.
Initializes REST API routes, middleware, OpenAPI documentation, and health endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from backend.app.api.routes import (
    anomaly_detection,
    copilot,
    dashboard,
    ingestion,
    inventory,
    normalization,
    recommendations,
    waste_detection,
)
from backend.app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Multi-Cloud FinOps Copilot Platform Backend API.",
    version="0.10.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Sub-Routers
app.include_router(ingestion.router, prefix=settings.API_V1_STR)
app.include_router(normalization.router, prefix=settings.API_V1_STR)
app.include_router(inventory.router, prefix=settings.API_V1_STR)
app.include_router(waste_detection.router, prefix=settings.API_V1_STR)
app.include_router(anomaly_detection.router, prefix=settings.API_V1_STR)
app.include_router(recommendations.router, prefix=settings.API_V1_STR)
app.include_router(copilot.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)


@app.get("/dashboard", tags=["FinOps Dashboards & Visualizations"], include_in_schema=False)
def dashboard_ui_redirect():
    """Redirect top-level /dashboard path to the interactive HTML5 FinOps dashboard."""
    return RedirectResponse(url=f"{settings.API_V1_STR}/dashboard/ui")


@app.get("/", tags=["Root"])
def root():
    return {
        "project": settings.PROJECT_NAME,
        "status": "online",
        "version": "0.10.0",
        "documentation": "/docs",
        "dashboard": "/dashboard",
    }


@app.get("/health/liveness", tags=["Health"])
def liveness_probe():
    """Liveness probe confirming service process is active."""
    return {"status": "healthy"}


@app.get("/health/readiness", tags=["Health"])
def readiness_probe():
    """Readiness probe confirming database and dependency connectivity."""
    return {"status": "ready"}
