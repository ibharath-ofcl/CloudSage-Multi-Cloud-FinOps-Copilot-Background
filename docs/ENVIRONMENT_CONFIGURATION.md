# CloudSage Environment Configuration & Secrets Management

## 1. Configuration Model

CloudSage utilizes Pydantic Settings (`backend/app/core/config.py`) to manage application parameters with support for environment variables, `.env` files, and strict production validation guards.

---

## 2. Parameter Reference Matrix

| Category | Variable | Default (Dev) | Production Standard | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Core** | `ENVIRONMENT` | `development` | `production` | Deployment environment profile (`development`, `test`, `production`). |
| | `PORT` | `8000` | `8000` | Internal HTTP listening port for ASGI server. |
| | `API_V1_STR` | `/api/v1` | `/api/v1` | Base URL prefix for REST API endpoints. |
| | `LOG_FORMAT` | `text` | `json` | Structured logging format (`text` or `json`). |
| | `LOG_LEVEL` | `INFO` | `INFO` | Root logging threshold. |
| **Database** | `POSTGRES_SERVER` | `localhost` | `postgres` (or RDS host) | PostgreSQL server hostname or cluster endpoint. |
| | `POSTGRES_PORT` | `5432` | `5432` | PostgreSQL listening port. |
| | `POSTGRES_USER` | `postgres` | `cloudsage_app` | Dedicated database application user. |
| | `POSTGRES_PASSWORD` | `postgres` | *High-entropy secret* | Database password ($\ge 32$ characters). |
| | `POSTGRES_DB` | `cloudsage` | `cloudsage_prod` | Target PostgreSQL database name. |
| | `DATABASE_URL` | *empty* | `postgresql+asyncpg://...` | Optional explicit async database URL with SSL. |
| | `SYNC_DATABASE_URL`| *empty* | `postgresql://...` | Optional explicit synchronous database URL for Alembic. |
| **Redis** | `REDIS_HOST` | `localhost` | `redis` (or ElastiCache) | Redis host. |
| | `REDIS_PORT` | `6379` | `6379` | Redis port. |
| | `REDIS_PASSWORD` | *empty* | *High-entropy secret* | Required in production. |
| **Security** | `SECRET_KEY` | `development-secret...` | *32+ char cryptographic secret* | Used for signing JWT tokens and HMAC signatures. |
| | `ALLOW_DEV_AUTH_HEADERS` | `true` | `false` | Enables/disables `X-User-Role` test header bypass. |
| | `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | `15` | Short-lived JWT expiration window. |
| | `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | `7` | Refresh token lifetime. |
| | `TRUSTED_PROXY_IPS` | `["127.0.0.1", "::1"]` | CIDR blocks of Ingress | Trusted reverse proxy IPs for client IP resolution. |
| **FinOps AI** | `COPILOT_ENABLED` | `true` | `true` | Enables AI FinOps Copilot features. |
| | `COPILOT_PROVIDER`| `auto` | `openai` | AI backend provider. |
| | `COPILOT_API_KEY` | *empty* | `sk-proj-...` | API key stored in secrets manager. |
| | `COPILOT_DEMO_MODE`| `true` | `false` | Demo mode fallback flag. |
| **Alerts** | `NOTIFICATION_SAFE_LOCAL_MODE` | `true` | `false` | In safe mode, notifications log locally; in prod, live dispatch. |
| | `SMTP_HOST` | `localhost` | Production SMTP relay | Email alert notification host. |
| | `SMTP_PORT` | `1025` | `587` | SMTP port. |

---

## 3. Production Validation Guards

When `ENVIRONMENT=production`, the application applies automated validators:
1. **Rejection of Default Secret:** Fails immediately if `SECRET_KEY` is equal to `"development-secret-key-change-in-production-stage"`.
2. **Secret Length Requirement:** Fails immediately if `len(SECRET_KEY) < 32`.
3. **RBAC Bypass Prohibition:** Fails immediately if `ALLOW_DEV_AUTH_HEADERS` is set to `True`.
4. **Default Database Password Rejection:** Fails immediately if `POSTGRES_PASSWORD` is left as `"postgres"`.
