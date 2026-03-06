# ClaimLens Deployment Guidelines V2 (EC2)

This guide describes how to deploy the **new semantic RAG changes** on an EC2 instance.

Scope of V2 deployment:

- `rag-system` ingestion + retrieval API
- Titan embeddings via Bedrock
- FAISS index persistence + S3 sync

---

## 1) Prerequisites

- EC2 Ubuntu 22.04+ instance (recommended `t3.medium` or above)
- IAM role attached to EC2 with permissions:
  - `bedrock:InvokeModel`
  - `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket`, `s3:HeadBucket`
- AWS Region where Bedrock model access is enabled (current code default: `us-east-1`)
- Open inbound security group ports:
  - `22` (SSH)
  - `8001` (RAG API, or keep private behind Nginx)

---

## 2) Bootstrap EC2

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git nginx
```

Clone project:

```bash
cd /opt
sudo git clone <YOUR_REPO_URL> claimlens
sudo chown -R $USER:$USER /opt/claimlens
cd /opt/claimlens
```

---

## 3) Configure Python Environment

```bash
cd /opt/claimlens/rag-system
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4) Prepare Runtime Directories

```bash
mkdir -p /opt/claimlens/rag-system/indexes
mkdir -p /opt/claimlens/rag-system/documents/policies
```

Add your policy PDFs to:

- `/opt/claimlens/rag-system/documents/policies/`

---

## 5) Verify AWS Access on EC2

```bash
aws sts get-caller-identity
```

If this fails:

- Attach/repair EC2 IAM role, or
- Configure credentials via environment (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`).

---

## 6) Initial Ingestion + Index Build

Start API once:

```bash
cd /opt/claimlens/rag-system
source .venv/bin/activate
uvicorn api.server:app --host 0.0.0.0 --port 8001
```

In another terminal:

```bash
curl -X POST http://<EC2_PUBLIC_IP>:8001/ingest
curl http://<EC2_PUBLIC_IP>:8001/health
```

Expected:

- `indexed_clauses` > 0
- `index_size` > 0

This also uploads FAISS bundle to S3 (`indexes/faiss.index`, `indexes/metadata.pkl`).

---

## 7) Run as a Systemd Service

Create service file:

```bash
sudo tee /etc/systemd/system/claimlens-rag.service > /dev/null << 'EOF'
[Unit]
Description=ClaimLens RAG API (V2)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/claimlens/rag-system
Environment="PYTHONUNBUFFERED=1"
ExecStart=/opt/claimlens/rag-system/.venv/bin/uvicorn api.server:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable claimlens-rag
sudo systemctl start claimlens-rag
sudo systemctl status claimlens-rag --no-pager
```

Logs:

```bash
journalctl -u claimlens-rag -f
```

---

## 8) Optional Nginx Reverse Proxy

Create Nginx site:

```bash
sudo tee /etc/nginx/sites-available/claimlens-rag > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
```

Enable config:

```bash
sudo ln -sf /etc/nginx/sites-available/claimlens-rag /etc/nginx/sites-enabled/claimlens-rag
sudo nginx -t
sudo systemctl restart nginx
```

---

## 9) Deploying New Changes Safely (Update Runbook)

```bash
cd /opt/claimlens
git pull origin <YOUR_BRANCH>
cd rag-system
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart claimlens-rag
curl http://127.0.0.1:8001/health
```

If ingestion logic changed or policies updated:

```bash
curl -X POST http://127.0.0.1:8001/ingest
```

---

## 10) Post-Deployment Verification Checklist

- `GET /health` returns `status=ok` and non-zero `index_size`.
- `GET /search` returns ranked clauses.
- Systemd service auto-restarts after reboot:

```bash
sudo reboot
# after reconnect
sudo systemctl status claimlens-rag --no-pager
```

- S3 index bundle is present and updated.

---

## 11) Rollback Plan

If a deployment fails:

1. Checkout previous stable commit/tag.
2. Reinstall deps if needed.
3. Restart service.
4. Validate with `/health` and `/search`.

Example:

```bash
cd /opt/claimlens
git checkout <PREVIOUS_STABLE_TAG>
cd rag-system
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart claimlens-rag
curl http://127.0.0.1:8001/health
```

---

## 12) Notes for This Repository

- Current `rag-system` code uses hardcoded defaults for:
  - region: `us-east-1`
  - bucket: `claimlens-faiss-index-1`
- Keep EC2 IAM and S3 bucket configuration aligned with these defaults unless you refactor to env-driven config.
- For app uploads/policy-chat, IAM should include the policy used in this setup (for example `ClaimLensS3AccessPolicy`) with object access on the configured bucket.

---

## 13) Policy-Chat Runtime Notes (Current)

- Policy processing now uses resilient embedding fallback:
  - primary configured mode (typically Bedrock)
  - fallback to local embeddings
  - fallback to mock embeddings
- This prevents `/api/v1/policies/process/{document_id}` from failing hard when Bedrock embedding calls fail.
- Storage diagnostics endpoint is available at:
  - `GET /api/v1/documents/storage-health`
  - It validates bucket access (`head`, `put`, `get`, `delete`) and returns actionable failures.
