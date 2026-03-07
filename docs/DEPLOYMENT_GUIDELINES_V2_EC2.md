# ClaimLens Deployment Guidelines V2 (EC2 + Docker)

This runbook replaces the old standalone `rag-system` deployment.

Current deployment in this repository is Docker-first and profile-based:

- `docker-compose.yml` with `prod` profile
- `backend` service (includes RAG + policy search/chat APIs)
- `frontend` service (Nginx static host + `/api` proxy)
- PostgreSQL + Redis containers (or external endpoints via `.env`)

---

## 1) Prerequisites

- EC2 AMI: `ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-20251212` (Ubuntu 22.04 LTS)
- Instance size: recommended `t3.medium` or above
- IAM role attached to EC2 with at least:
  - `bedrock:InvokeModel`
  - `s3:ListBucket`, `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:HeadBucket`
- Bedrock model access enabled in your chosen region
- Security group inbound (minimum):
  - `22` (SSH)
  - `80` (frontend)
  - `8000` (backend API/direct health checks, optional if private)

---

## 2) Bootstrap EC2 (Docker Host)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl ca-certificates gnupg lsb-release

# Install Docker Engine + Compose plugin
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Optional sanity checks
docker --version
docker compose version
```

Clone repository:

```bash
cd /opt
sudo git clone <YOUR_REPO_URL> claimlens
sudo chown -R $USER:$USER /opt/claimlens
cd /opt/claimlens
```

---

## 3) Configure Production Environment

```bash
cd /opt/claimlens
cp .env.sample .env
```

Update `.env` for production (required):

```dotenv
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security
SECRET_KEY=<secure-random-value>
CORS_ORIGINS=https://<your-domain>

# Data stores (can be external or local docker services)
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<db-host>:5432/claimlens
REDIS_URL=redis://:<password>@<redis-host>:6379/0

# AWS
AWS_REGION=<your-bedrock-region>
AWS_ACCESS_KEY_ID=<access-key-or-use-iam-role>
AWS_SECRET_ACCESS_KEY=<secret-key-or-use-iam-role>
S3_BUCKET_NAME=<your-bucket>
USE_LOCALSTACK=false
S3_ENDPOINT_URL=
AWS_ENDPOINT_URL=

# LLM / Embeddings
USE_MOCK_LLM=false
BEDROCK_ENABLED=true
EMBEDDING_MODE=bedrock
BEDROCK_MODEL_ID=amazon.titan-embed-text-v1
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1
```

Notes:

- If `DATABASE_URL` points to `@db:5432`, compose `prod` uses local docker DB service.
- If using EC2 IAM role, you can leave static AWS keys empty.
- Keep `BEDROCK_MODEL_ID` as an LLM model (not Titan embedding model).

---

## 4) Start Production Stack (Docker)

Recommended (project script):

```bash
cd /opt/claimlens
chmod +x docker-manage.sh
./docker-manage.sh start prod
```

Equivalent raw compose command:

```bash
docker compose --profile prod up -d --build
```

Check status/logs:

```bash
./docker-manage.sh status
./docker-manage.sh logs backend
./docker-manage.sh logs frontend
```

---

## 5) Database Migration

Run migrations once backend is up:

```bash
cd /opt/claimlens
./docker-manage.sh migrate
```

If using local Docker PostgreSQL and pgvector needs repair:

```bash
./docker-manage.sh fix-postgres
```

---

## 6) Post-Deployment Verification

Core health checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1/
```

Expected backend health shape:

- `status` should be `healthy`
- response includes `environment` and `version`

Frontend reachability:

```bash
curl -I http://127.0.0.1/
```

Storage diagnostics endpoint (auth required):

1. Obtain JWT via `/api/v1/auth/login`
2. Call:

```bash
curl -H "Authorization: Bearer <TOKEN>" \
  http://127.0.0.1:8000/api/v1/documents/storage-health
```

It validates S3 `head/put/get/delete` and returns actionable failures.

---

## 7) RAG / Policy APIs (Current Endpoints)

The old `/ingest` and standalone `rag-system` API are not the active path in latest code.

Use these endpoints instead (all under backend API):

- `POST /api/v1/policies/process/{document_id}`
- `POST /api/v1/policies/search`
- `POST /api/v1/policies/chat`
- `GET /api/v1/documents/storage-health`

Runtime behavior includes embedding fallback:

- primary configured mode (typically Bedrock)
- fallback to local embeddings
- fallback to mock embeddings

---

## 8) Optional: Run on Boot with systemd (Docker Compose)

Create service:

```bash
sudo tee /etc/systemd/system/claimlens-docker.service > /dev/null << 'EOF'
[Unit]
Description=ClaimLens Docker Compose Stack
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
WorkingDirectory=/opt/claimlens
ExecStart=/usr/bin/docker compose --profile prod up -d --build
ExecStop=/usr/bin/docker compose --profile prod down
RemainAfterExit=yes
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
```

Enable/start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable claimlens-docker
sudo systemctl start claimlens-docker
sudo systemctl status claimlens-docker --no-pager
```

---

## 9) Safe Update Runbook

```bash
cd /opt/claimlens
git pull origin <YOUR_BRANCH>

# Refresh services
./docker-manage.sh restart prod

# Re-run migrations if schema changed
./docker-manage.sh migrate

# Verify
curl http://127.0.0.1:8000/health
```

---

## 10) Rollback Plan

```bash
cd /opt/claimlens
git checkout <PREVIOUS_STABLE_TAG_OR_COMMIT>
./docker-manage.sh restart prod
./docker-manage.sh migrate
curl http://127.0.0.1:8000/health
```

If using local DB volumes and rollback needs data reset/restore:

```bash
./docker-manage.sh backup
./docker-manage.sh restore --auto
```

---

## 11) Quick Troubleshooting

- Backend not healthy:
  - `./docker-manage.sh logs backend`
  - verify `.env` (`DATABASE_URL`, `REDIS_URL`, `BEDROCK_ENABLED`, `S3_BUCKET_NAME`)
- AWS/Bedrock errors:
  - validate IAM role permissions and region
  - ensure Bedrock model access is enabled in configured region
- S3 upload/diagnostic failures:
  - test `GET /api/v1/documents/storage-health` with valid JWT
- Port conflicts:
  - check `80`, `8000`, `5432`, `6379`

---

## 12) Command Reference

```bash
./docker-manage.sh start prod
./docker-manage.sh stop
./docker-manage.sh restart prod
./docker-manage.sh status
./docker-manage.sh logs
./docker-manage.sh exec backend
./docker-manage.sh migrate
./docker-manage.sh backup
./docker-manage.sh restore
```
