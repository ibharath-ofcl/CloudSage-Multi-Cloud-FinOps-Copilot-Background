# CloudSage Local Deployment Guide

## 1. Prerequisites

Before running CloudSage locally, ensure the following software is installed on your workstation:
- **Docker Engine:** Version 24.0 or higher
- **Docker Compose:** Version 2.20 or higher
- **Python:** Version 3.11+ (optional, for native development without Docker)
- **Node.js:** Version 18+ (optional, for frontend UI hacking)

---

## 2. Quickstart with Docker Compose

To spin up the entire CloudSage multi-cloud FinOps platform with a single command:

```bash
# 1. Clone repository and navigate to root
git clone https://github.com/ibharath-ofcl/CloudSage-Multi-Cloud-FinOps-Copilot-Background.git
cd CloudSage-Multi-Cloud-FinOps-Copilot-Background

# 2. Prepare environment configuration
cp .env.example .env

# 3. Launch container stack
docker compose up -d --build
```

### Verification & Health Checking
Monitor container startup:
```bash
docker compose ps
docker compose logs -f backend
```

Once containers are initialized:
| Service | URL / Port | Credentials / Notes |
| :--- | :--- | :--- |
| **Frontend UI** | [http://localhost:3000](http://localhost:3000) | Interactive FinOps Command Center |
| **Backend REST API** | [http://localhost:8000](http://localhost:8000) | FastAPI Engine |
| **Interactive API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger OpenAPI UI |
| **Liveness Probe** | [http://localhost:8000/health/liveness](http://localhost:8000/health/liveness) | `{"status":"healthy"}` |
| **Readiness Probe** | [http://localhost:8000/health/readiness](http://localhost:8000/health/readiness) | `{"status":"ready"}` |
| **Dependencies Health** | [http://localhost:8000/health/dependencies](http://localhost:8000/health/dependencies) | Component Latency & Health |
| **Prometheus Metrics** | [http://localhost:8000/metrics](http://localhost:8000/metrics) | Scrape Endpoint |
| **PostgreSQL Database** | `localhost:5432` | User: `postgres`, DB: `cloudsage` |
| **Redis Cache** | `localhost:6379` | Port 6379 |

---

## 3. Native Development Setup (Without Docker)

If developing locally without Docker:

### Backend Setup:
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run migrations
alembic -c backend/alembic.ini upgrade head

# Start application server
uvicorn backend.app.main:app --reload --port 8000
```

### Frontend Setup:
```bash
cd frontend
npm install
npm run dev
```

---

## 4. Running the Test Suite Locally

```bash
# Execute full test suite (567 passing tests)
pytest backend/tests/ -v

# Run Stage 15 deployment readiness demonstration
python3 backend/scripts/demo_stage15_deployment.py
```

---

## 5. Stopping the Environment

To stop and remove containers while preserving persistent volumes:
```bash
docker compose down
```

To stop containers and reset the database volume:
```bash
docker compose down -v
```
