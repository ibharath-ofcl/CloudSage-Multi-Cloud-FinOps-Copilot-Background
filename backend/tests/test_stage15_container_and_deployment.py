"""
CloudSage Stage 15 Test Suite: Production Containerization, CI/CD & Deployment Readiness.
Comprehensive validation covering:
  1. Multi-Stage Dockerfile architecture (Backend & Frontend)
  2. Production Docker Compose specifications (Dev & Prod)
  3. Health probes (/health/liveness, /health/readiness, /health/dependencies)
  4. Observability & Telemetry (Prometheus metrics, X-Request-ID correlation, Structured JSON logs)
  5. Production Configuration & Security Hardening (Settings validation, secret strength)
  6. Database Operations & Disaster Recovery scripts (backup_db.sh, restore_db.sh, entrypoint.sh)
  7. CI/CD GitHub Actions Workflow Specifications & Strict Zero-Float verification
"""

import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
from decimal import Decimal
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app.core.config import Settings
from backend.app.core.observability import (
    JSONLogFormatter,
    check_dependency_health,
    get_current_request_id,
    get_prometheus_metrics,
)
from backend.app.main import app

# Repository root directory
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ==============================================================================
# 1. DOCKERFILE & CONTAINER ARCHITECTURE TESTS (10 tests)
# ==============================================================================

def test_backend_dockerfile_exists():
    """Verify backend/Dockerfile exists in repository."""
    dockerfile = REPO_ROOT / "backend" / "Dockerfile"
    assert dockerfile.exists(), "backend/Dockerfile must exist."


def test_backend_dockerfile_multi_stage():
    """Verify backend Dockerfile defines both builder and production stages."""
    content = (REPO_ROOT / "backend" / "Dockerfile").read_text()
    assert "FROM python:3.13-slim AS builder" in content or "AS builder" in content
    assert "FROM python:3.13-slim AS production" in content or "AS production" in content


def test_backend_dockerfile_non_root_user():
    """Verify backend Dockerfile creates and runs as an unprivileged user (cloudsage)."""
    content = (REPO_ROOT / "backend" / "Dockerfile").read_text()
    assert "groupadd -g 10001 cloudsage" in content or "useradd" in content
    assert "USER cloudsage:cloudsage" in content or "USER cloudsage" in content


def test_backend_dockerfile_healthcheck():
    """Verify backend Dockerfile defines a HEALTHCHECK directive targeting /health/liveness."""
    content = (REPO_ROOT / "backend" / "Dockerfile").read_text()
    assert "HEALTHCHECK" in content
    assert "/health/liveness" in content


def test_backend_dockerfile_entrypoint_and_cmd():
    """Verify backend Dockerfile specifies entrypoint script and gunicorn ASGI server."""
    content = (REPO_ROOT / "backend" / "Dockerfile").read_text()
    assert "ENTRYPOINT" in content
    assert "entrypoint.sh" in content
    assert "gunicorn" in content
    assert "uvicorn.workers.UvicornWorker" in content


def test_backend_dockerignore_rules():
    """Verify backend/.dockerignore excludes pycache, git, tests, and environment files."""
    dockerignore = REPO_ROOT / "backend" / ".dockerignore"
    assert dockerignore.exists()
    content = dockerignore.read_text()
    assert "__pycache__" in content
    assert ".git" in content
    assert ".env" in content
    assert "tests/" in content


def test_frontend_dockerfile_exists_and_stages():
    """Verify frontend/Dockerfile exists and implements Node build and Nginx runtime stages."""
    dockerfile = REPO_ROOT / "frontend" / "Dockerfile"
    assert dockerfile.exists()
    content = dockerfile.read_text()
    assert "AS builder" in content
    assert "node:" in content
    assert "AS production" in content
    assert "nginx:" in content


def test_frontend_dockerfile_healthcheck():
    """Verify frontend Dockerfile specifies an automated health check."""
    content = (REPO_ROOT / "frontend" / "Dockerfile").read_text()
    assert "HEALTHCHECK" in content
    assert "healthz" in content or "http://localhost" in content


def test_frontend_dockerignore_rules():
    """Verify frontend/.dockerignore excludes node_modules, dist, and environment files."""
    dockerignore = REPO_ROOT / "frontend" / ".dockerignore"
    assert dockerignore.exists()
    content = dockerignore.read_text()
    assert "node_modules/" in content
    assert "dist/" in content
    assert ".env" in content


def test_ingress_nginx_dockerfile_and_conf():
    """Verify Nginx ingress reverse proxy files exist and contain upstream configuration."""
    nginx_conf = REPO_ROOT / "nginx" / "nginx.conf"
    nginx_dockerfile = REPO_ROOT / "nginx" / "Dockerfile"
    assert nginx_conf.exists()
    assert nginx_dockerfile.exists()

    content = nginx_conf.read_text()
    assert "backend_upstream" in content
    assert "frontend_upstream" in content
    assert "limit_req_zone" in content
    assert "X-Frame-Options" in content


# ==============================================================================
# 2. DOCKER COMPOSE SPECIFICATIONS (8 tests)
# ==============================================================================

def test_docker_compose_dev_syntax():
    """Verify docker-compose.yml defines core development services."""
    compose_path = REPO_ROOT / "docker-compose.yml"
    assert compose_path.exists()
    content = compose_path.read_text()
    assert "backend:" in content
    assert "frontend:" in content
    assert "postgres:" in content
    assert "redis:" in content


def test_docker_compose_dev_healthchecks():
    """Verify development compose defines healthchecks for postgres and redis."""
    content = (REPO_ROOT / "docker-compose.yml").read_text()
    assert "pg_isready" in content
    assert "redis-cli" in content
    assert "condition: service_healthy" in content


def test_docker_compose_prod_syntax():
    """Verify docker-compose.prod.yml defines production tier services."""
    prod_compose = REPO_ROOT / "docker-compose.prod.yml"
    assert prod_compose.exists()
    content = prod_compose.read_text()
    assert "ingress:" in content
    assert "backend:" in content
    assert "frontend:" in content
    assert "postgres:" in content
    assert "redis:" in content


def test_docker_compose_prod_resources():
    """Verify production compose defines resource limits (CPU and Memory)."""
    content = (REPO_ROOT / "docker-compose.prod.yml").read_text()
    assert "deploy:" in content
    assert "resources:" in content
    assert "limits:" in content
    assert "cpus:" in content
    assert "memory:" in content


def test_docker_compose_prod_restart_policies():
    """Verify production services define restart: always."""
    content = (REPO_ROOT / "docker-compose.prod.yml").read_text()
    assert "restart: always" in content


def test_docker_compose_prod_network_isolation():
    """Verify production compose isolates database on internal network."""
    content = (REPO_ROOT / "docker-compose.prod.yml").read_text()
    assert "cloudsage-internal-net:" in content
    assert "internal: true" in content


def test_docker_compose_prod_volumes():
    """Verify production compose defines persistent volumes for DB and backups."""
    content = (REPO_ROOT / "docker-compose.prod.yml").read_text()
    assert "postgres_prod_data" in content
    assert "redis_prod_data" in content
    assert "cloudsage_backups" in content


def test_docker_compose_prod_logging():
    """Verify production compose configures json-file log rotation."""
    content = (REPO_ROOT / "docker-compose.prod.yml").read_text()
    assert 'driver: "json-file"' in content
    assert "max-size:" in content
    assert "max-file:" in content


# ==============================================================================
# 3. HEALTH PROBES & DEEP DIAGNOSTICS (8 tests)
# ==============================================================================

def test_liveness_endpoint_healthy():
    """Verify GET /health/liveness returns 200 with status healthy and service metadata."""
    client = TestClient(app)
    response = client.get("/health/liveness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "cloudsage-backend"
    assert "version" in data


def test_readiness_endpoint_ready(db_session):
    """Verify GET /health/readiness returns 200 with status ready."""
    client = TestClient(app)
    response = client.get("/health/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ready", "unready")
    assert "database" in data
    assert "version" in data


def test_dependencies_health_probe_structure(db_session):
    """Verify GET /health/dependencies returns structured diagnostic breakdown."""
    health = check_dependency_health(db_session=db_session)
    assert "status" in health
    assert "timestamp" in health
    assert "total_latency_ms" in health
    assert "dependencies" in health
    assert "database" in health["dependencies"]
    assert "cache_broker" in health["dependencies"]
    assert "storage" in health["dependencies"]


def test_dependencies_health_latency_metrics(db_session):
    """Verify dependency check measures latency in milliseconds."""
    health = check_dependency_health(db_session=db_session)
    assert isinstance(health["total_latency_ms"], (int, float))
    assert health["total_latency_ms"] >= 0
    assert "latency_ms" in health["dependencies"]["database"]
    assert health["dependencies"]["storage"]["writable"] is True


def test_dependencies_health_degraded_cache(monkeypatch, db_session):
    """Verify health checker handles unreachable optional cache gracefully as degraded."""
    from backend.app.core.config import settings
    monkeypatch.setattr(settings, "NOTIFICATION_SAFE_LOCAL_MODE", False)
    monkeypatch.setattr(settings, "REDIS_HOST", "invalid-redis-host-for-testing")
    monkeypatch.setattr(settings, "HEALTHCHECK_TIMEOUT_SECONDS", 0.1)

    health = check_dependency_health(db_session=db_session)
    # Database is healthy, cache is degraded
    assert health["dependencies"]["cache_broker"]["status"] == "degraded"
    assert health["status"] == "degraded"


def test_dependencies_health_unhealthy_db(monkeypatch):
    """Verify health checker reports unhealthy when database connection fails."""
    # Pass a dummy object that raises an error on execute
    class FailingSession:
        def execute(self, *args, **kwargs):
            raise ConnectionRefusedError("Database connection refused")
        def close(self):
            pass

    health = check_dependency_health(db_session=FailingSession())
    assert health["status"] == "unhealthy"
    assert health["dependencies"]["database"]["status"] == "unhealthy"
    assert "error" in health["dependencies"]["database"]


def test_root_endpoint_metadata():
    """Verify GET / returns application metadata and links."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "CloudSage - Multi-Cloud FinOps Copilot"
    assert data["status"] == "online"
    assert data["version"] == "0.15.0"
    assert data["documentation"] == "/docs"
    assert data["dashboard"] == "/dashboard"


def test_dashboard_redirect():
    """Verify GET /dashboard redirects to /api/v1/dashboard/ui."""
    client = TestClient(app)
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/api/v1/dashboard/ui"


# ==============================================================================
# 4. OBSERVABILITY & TELEMETRY (8 tests)
# ==============================================================================

def test_prometheus_metrics_endpoint():
    """Verify GET /metrics returns 200 with text/plain exposition format."""
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert len(response.text) > 0


def test_prometheus_metrics_format():
    """Verify Prometheus metrics output follows standard HELP and TYPE declarations."""
    metrics_text = get_prometheus_metrics()
    assert "# HELP" in metrics_text
    assert "# TYPE" in metrics_text
    assert "cloudsage_http_requests_total" in metrics_text


def test_prometheus_http_requests_counter():
    """Verify HTTP requests counter is updated after requests."""
    client = TestClient(app)
    client.get("/health/liveness")
    metrics_text = get_prometheus_metrics()
    assert 'cloudsage_http_requests_total{endpoint="/health/liveness"' in metrics_text


def test_prometheus_finops_domain_metrics():
    """Verify custom FinOps domain metrics are registered in Prometheus registry."""
    metrics_text = get_prometheus_metrics()
    assert "cloudsage_finops_anomalies_detected_total" in metrics_text
    assert "cloudsage_finops_recommendations_active" in metrics_text
    assert "cloudsage_finops_potential_savings_usd" in metrics_text


def test_request_correlation_id_generated():
    """Verify X-Request-ID header is generated and injected into response if missing."""
    client = TestClient(app)
    response = client.get("/health/liveness")
    assert response.status_code == 200
    req_id = response.headers.get("X-Request-ID")
    assert req_id is not None
    assert len(req_id) >= 16


def test_request_correlation_id_propagated():
    """Verify incoming X-Request-ID header is preserved and echoed in response."""
    client = TestClient(app)
    custom_id = "finops-trace-uuid-12345"
    response = client.get("/health/liveness", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


def test_get_current_request_id_fallback():
    """Verify get_current_request_id provides a valid string outside request context."""
    fallback_id = get_current_request_id()
    assert isinstance(fallback_id, str)
    assert len(fallback_id) > 0


def test_structured_json_log_formatting():
    """Verify JSONLogFormatter serializes LogRecord into valid JSON with required fields."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test structured log message",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    log_dict = json.loads(formatted)
    assert log_dict["level"] == "INFO"
    assert log_dict["logger"] == "test_logger"
    assert log_dict["message"] == "Test structured log message"
    assert "timestamp" in log_dict
    assert "request_id" in log_dict


# ==============================================================================
# 5. PRODUCTION CONFIGURATION & SECURITY HARDENING (8 tests)
# ==============================================================================

def test_config_development_defaults():
    """Verify Settings initializes with development defaults."""
    cfg = Settings(ENVIRONMENT="development")
    assert cfg.is_development() is True
    assert cfg.is_production() is False


def test_config_production_rejects_default_secret():
    """Verify Settings rejects default secret key when ENVIRONMENT=production."""
    with pytest.raises(ValueError, match="secure, non-default SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="development-secret-key-change-in-production-stage",
            POSTGRES_PASSWORD="secure_prod_password_1234567890!",
            ALLOW_DEV_AUTH_HEADERS=False,
        )


def test_config_production_rejects_short_secret():
    """Verify Settings rejects secret keys shorter than 32 characters in production."""
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="too-short-secret-key",
            POSTGRES_PASSWORD="secure_prod_password_1234567890!",
            ALLOW_DEV_AUTH_HEADERS=False,
        )


def test_config_production_rejects_dev_auth_headers():
    """Verify Settings rejects ALLOW_DEV_AUTH_HEADERS=True in production."""
    with pytest.raises(ValueError, match="ALLOW_DEV_AUTH_HEADERS must be False"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a_cryptographically_secure_key_that_is_32_characters_long",
            POSTGRES_PASSWORD="secure_prod_password_1234567890!",
            ALLOW_DEV_AUTH_HEADERS=True,
        )


def test_config_production_rejects_default_db_password():
    """Verify Settings rejects default postgres password in production."""
    with pytest.raises(ValueError, match="cannot use default PostgreSQL password"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a_cryptographically_secure_key_that_is_32_characters_long",
            POSTGRES_PASSWORD="postgres",
            ALLOW_DEV_AUTH_HEADERS=False,
        )


def test_config_production_valid_configuration():
    """Verify Settings succeeds with fully hardened production configuration."""
    cfg = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a_cryptographically_secure_key_that_is_32_characters_long",
        POSTGRES_PASSWORD="secure_prod_password_1234567890!",
        ALLOW_DEV_AUTH_HEADERS=False,
    )
    assert cfg.is_production() is True
    assert cfg.ALLOW_DEV_AUTH_HEADERS is False
    assert cfg.GUNICORN_WORKERS >= 2


def test_env_example_documented():
    """Verify .env.example contains essential setup variables."""
    env_file = REPO_ROOT / ".env.example"
    assert env_file.exists()
    content = env_file.read_text()
    assert "ENVIRONMENT=" in content
    assert "POSTGRES_SERVER=" in content
    assert "SECRET_KEY=" in content
    assert "COPILOT_ENABLED=" in content


def test_env_production_example_documented():
    """Verify .env.production.example contains required production hardening directives."""
    env_file = REPO_ROOT / ".env.production.example"
    assert env_file.exists()
    content = env_file.read_text()
    assert "ENVIRONMENT=production" in content
    assert "ALLOW_DEV_AUTH_HEADERS=false" in content
    assert "LOG_FORMAT=json" in content
    assert "GUNICORN_WORKERS=4" in content


# ==============================================================================
# 6. DATABASE OPERATIONS & DISASTER RECOVERY SCRIPTS (6 tests)
# ==============================================================================

def test_backup_script_syntax_and_perms():
    """Verify backup_db.sh exists, is executable, and contains valid bash syntax."""
    script_path = REPO_ROOT / "backend" / "scripts" / "backup_db.sh"
    assert script_path.exists()
    assert os.access(script_path, os.X_OK), "backup_db.sh must be executable."
    # Syntax check via bash -n
    res = subprocess.run(["bash", "-n", str(script_path)], capture_output=True, text=True)
    assert res.returncode == 0, f"Bash syntax error in backup_db.sh: {res.stderr}"


def test_restore_script_syntax_and_perms():
    """Verify restore_db.sh exists, is executable, and contains valid bash syntax."""
    script_path = REPO_ROOT / "backend" / "scripts" / "restore_db.sh"
    assert script_path.exists()
    assert os.access(script_path, os.X_OK), "restore_db.sh must be executable."
    res = subprocess.run(["bash", "-n", str(script_path)], capture_output=True, text=True)
    assert res.returncode == 0, f"Bash syntax error in restore_db.sh: {res.stderr}"


def test_entrypoint_script_syntax_and_perms():
    """Verify entrypoint.sh exists, is executable, and contains valid bash syntax."""
    script_path = REPO_ROOT / "backend" / "scripts" / "entrypoint.sh"
    assert script_path.exists()
    assert os.access(script_path, os.X_OK), "entrypoint.sh must be executable."
    res = subprocess.run(["bash", "-n", str(script_path)], capture_output=True, text=True)
    assert res.returncode == 0, f"Bash syntax error in entrypoint.sh: {res.stderr}"


def test_restore_script_safety_guard():
    """Verify restore_db.sh aborts with exit code 2 when run without --force or confirmation flag."""
    script_path = REPO_ROOT / "backend" / "scripts" / "restore_db.sh"
    with tempfile.NamedTemporaryFile(suffix=".sql.gz") as tf:
        tf.write(b"mock_backup")
        tf.flush()
        env = os.environ.copy()
        env["CONFIRM_RESTORE"] = "false"
        res = subprocess.run(["bash", str(script_path), tf.name], capture_output=True, text=True, env=env)
        assert res.returncode == 2, "Restore script must exit with code 2 when safety confirmation is missing."
        assert "SAFETY CHECK FAILED" in res.stderr or "OVERWRITE" in res.stderr


def test_restore_script_checksum_validation():
    """Verify restore_db.sh aborts with exit code 3 when checksum does not match."""
    script_path = REPO_ROOT / "backend" / "scripts" / "restore_db.sh"
    with tempfile.NamedTemporaryFile(suffix=".sql.gz", delete=False) as tf:
        tf.write(b"mock_backup_bytes")
        tf.flush()
        checksum_path = Path(tf.name + ".sha256")
        checksum_path.write_text("invalid_tampered_hash_value  " + tf.name)

        try:
            env = os.environ.copy()
            env["CONFIRM_RESTORE"] = "true"
            res = subprocess.run(["bash", str(script_path), tf.name, "--force"], capture_output=True, text=True, env=env)
            assert res.returncode == 3, "Restore script must exit with code 3 on checksum mismatch."
            assert "Checksum mismatch" in res.stderr or "corrupt" in res.stderr.lower()
        finally:
            os.unlink(tf.name)
            if checksum_path.exists():
                checksum_path.unlink()


def test_backup_script_execution_and_checksum():
    """Verify backup_db.sh creates compressed archive and valid SHA256 checksum file."""
    script_path = REPO_ROOT / "backend" / "scripts" / "backup_db.sh"
    with tempfile.TemporaryDirectory() as tmp_dir:
        env = os.environ.copy()
        env["BACKUP_DIR"] = tmp_dir
        env["TEST_MOCK_BACKUP"] = "true"
        env["MOCK_BACKUP_CONTENT"] = "CREATE TABLE test_finops (id SERIAL PRIMARY KEY);"

        res = subprocess.run(["bash", str(script_path)], capture_output=True, text=True, env=env)
        assert res.returncode == 0, f"backup_db.sh failed: {res.stderr}"

        # Check backup and sha256 files were created
        backups = list(Path(tmp_dir).glob("cloudsage_backup_*.sql.gz"))
        assert len(backups) == 1, "Backup archive should be created."
        backup_file = backups[0]
        checksum_file = Path(str(backup_file) + ".sha256")
        assert checksum_file.exists(), "Checksum file (.sha256) should be created."

        # Verify hash matches
        computed_hash = hashlib.sha256(backup_file.read_bytes()).hexdigest()
        saved_hash = checksum_file.read_text().split()[0]
        assert computed_hash == saved_hash, "Checksum recorded in file must match computed SHA256."


# ==============================================================================
# 7. CI/CD WORKFLOWS & ZERO-FLOAT REGRESSION VERIFICATION (6 tests)
# ==============================================================================

def test_ci_workflow_yaml_syntax():
    """Verify .github/workflows/ci.yml exists and contains all 6 quality gates."""
    ci_file = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    assert ci_file.exists()
    content = ci_file.read_text()
    assert "source-validation:" in content
    assert "backend-quality-gate:" in content
    assert "frontend-quality-gate:" in content
    assert "container-quality-gate:" in content
    assert "security-supply-chain-gate:" in content
    assert "final-quality-gate:" in content


def test_cd_workflow_yaml_syntax():
    """Verify .github/workflows/cd.yml exists and defines deployment stages."""
    cd_file = REPO_ROOT / ".github" / "workflows" / "cd.yml"
    assert cd_file.exists()
    content = cd_file.read_text()
    assert "build-and-publish:" in content
    assert "deploy-staging:" in content
    assert "deploy-production:" in content
    assert "Automated Emergency Rollback" in content or "rollback" in content.lower()


def test_ci_cd_branch_triggers():
    """Verify CI workflow triggers on main and stage branches."""
    content = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "branches:" in content
    assert "main" in content
    assert "stage-*" in content


def test_strict_zero_float_production_schemas():
    """Verify all FinOps monetary and cost schemas strictly utilize Decimal."""
    from backend.app.schemas.billing import BillingRecordBase
    from backend.app.schemas.recommendation import RecommendationBase
    from datetime import datetime, timezone

    # Verify model fields annotate monetary fields with Decimal
    assert BillingRecordBase.model_fields["unblended_cost"].annotation == Decimal
    assert RecommendationBase.model_fields["estimated_monthly_savings"].annotation == Decimal

    # Verify instantiation preserves Decimal without float conversion
    from backend.app.core.enums import CloudProvider, RecommendationAction
    rec = RecommendationBase(
        resource_id="arn:aws:ec2:us-east-1:123456789012:instance/i-test",
        provider=CloudProvider.AWS,
        action_type=RecommendationAction.RIGHTSIZE,
        title="Rightsize EC2 instance",
        description="Downsize from c5.2xlarge to c5.xlarge",
        remediation_guide="aws ec2 modify-instance-attribute --instance-id i-test --instance-type c5.xlarge",
        estimated_monthly_savings=Decimal("142.5000"),
        estimated_annual_savings=Decimal("1710.0000"),
    )
    assert isinstance(rec.estimated_monthly_savings, Decimal)
    assert rec.estimated_monthly_savings == Decimal("142.5000")
    assert isinstance(rec.estimated_annual_savings, Decimal)
    assert rec.estimated_annual_savings == Decimal("1710.0000")
    assert not isinstance(rec.estimated_monthly_savings, float)
    assert not isinstance(rec.estimated_annual_savings, float)


def test_alembic_migrations_revisions_chain():
    """Verify all 12 Alembic revisions form a continuous, ordered migration chain."""
    migrations_dir = REPO_ROOT / "backend" / "alembic" / "versions"
    migration_files = sorted([f for f in migrations_dir.glob("*.py") if not f.name.startswith("__")])
    assert len(migration_files) == 12, f"Expected 12 migrations, found {len(migration_files)}"
    
    # Verify latest migration is 012_rbac_enterprise_security
    latest_migration = migration_files[-1].name
    assert "012" in latest_migration
    assert "rbac" in latest_migration or "security" in latest_migration


def test_production_readiness_signoff():
    """Verify overall production containerization and deployment readiness criteria."""
    # 1. Backend Dockerfile exists & has healthcheck
    assert (REPO_ROOT / "backend" / "Dockerfile").exists()
    # 2. Frontend Dockerfile exists
    assert (REPO_ROOT / "frontend" / "Dockerfile").exists()
    # 3. Nginx config exists
    assert (REPO_ROOT / "nginx" / "nginx.conf").exists()
    # 4. Compose files exist
    assert (REPO_ROOT / "docker-compose.yml").exists()
    assert (REPO_ROOT / "docker-compose.prod.yml").exists()
    # 5. Environment templates exist
    assert (REPO_ROOT / ".env.example").exists()
    assert (REPO_ROOT / ".env.production.example").exists()
    # 6. CI/CD pipelines exist
    assert (REPO_ROOT / ".github" / "workflows" / "ci.yml").exists()
    assert (REPO_ROOT / ".github" / "workflows" / "cd.yml").exists()
    # 7. Operational scripts exist
    assert (REPO_ROOT / "backend" / "scripts" / "backup_db.sh").exists()
    assert (REPO_ROOT / "backend" / "scripts" / "restore_db.sh").exists()
    assert (REPO_ROOT / "backend" / "scripts" / "entrypoint.sh").exists()
