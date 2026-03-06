# ClaimLens Deployment Guide

A comprehensive guide for deploying ClaimLens in **Local Development** and **Production (AWS)** environments.

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Local Development Setup](#local-development-setup)
3. [Production AWS Setup](#production-aws-setup)
4. [Environment Configuration](#environment-configuration)
5. [Troubleshooting](#troubleshooting)

---

## Quick Reference

| Environment | Command | LLM | Database | Storage |
|-------------|---------|-----|----------|---------|
| **Local** | `./docker-manage.sh start local` | Mock (Free) | Local PostgreSQL | LocalStack S3 |
| **Production** | `./docker-manage.sh start prod` | AWS Bedrock | AWS RDS | AWS S3 |

---

## Local Development Setup

### Prerequisites

- Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- Docker Compose v2.0+
- 8GB RAM minimum (for all containers)
- 10GB disk space

### Step 1: Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd ClaimLens-AI4Bharat

# Copy environment template
cp .env.sample .env
```

### Step 2: Start Local Development

```bash
# Start all services
./docker-manage.sh start local
```

This command will:
1. ✅ Build Docker images with hot-reload support
2. ✅ Start PostgreSQL database with pgvector extension
3. ✅ Start Redis for caching
4. ✅ Start LocalStack for S3 emulation
5. ✅ Start Backend API (FastAPI) with auto-reload
6. ✅ Start Frontend (React) with hot-reload
7. ✅ Run database migrations automatically

### Step 3: Access the Application

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:3000 | React application |
| Backend API | http://localhost:8000 | FastAPI server |
| Swagger Docs | http://localhost:8000/docs | API documentation |
| ReDoc | http://localhost:8000/redoc | Alternative API docs |
| LocalStack | http://localhost:4566 | AWS S3 emulation |

### Step 4: Development Workflow

```bash
# View logs
./docker-manage.sh logs              # All services
./docker-manage.sh logs backend      # Backend only
./docker-manage.sh logs frontend     # Frontend only

# Access container shell
./docker-manage.sh exec backend      # Backend bash
./docker-manage.sh exec db           # PostgreSQL psql

# Run database migrations
./docker-manage.sh migrate

# Stop services
./docker-manage.sh stop

# Stop and remove all data
./docker-manage.sh stop --volumes
```

### What's Running in Local Mode

```
┌──────────────────────────────────────────────────────────────┐
│                    LOCAL DEVELOPMENT MODE                     │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│   Browser ──► Frontend (React Dev Server :3000)              │
│                        │                                      │
│                        ▼                                      │
│              Backend (FastAPI :8000)                          │
│                 │         │         │                         │
│                 ▼         ▼         ▼                         │
│         ┌──────────┐ ┌───────┐ ┌────────────┐               │
│         │PostgreSQL│ │ Redis │ │ LocalStack │               │
│         │ pgvector │ │       │ │    S3      │               │
│         │  :5432   │ │ :6379 │ │   :4566    │               │
│         └──────────┘ └───────┘ └────────────┘               │
│                                                               │
│   Mock LLM: Returns simulated AI responses (no AWS costs)    │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Production AWS Setup

### Prerequisites

- AWS Account with appropriate permissions
- AWS CLI installed and configured
- Domain name (optional, for custom domain)
- Docker and Docker Compose

### AWS Services Required

| Service | Purpose | Estimated Cost |
|---------|---------|----------------|
| **EC2** | Host Docker containers | ~$20-50/month (t3.medium) |
| **RDS PostgreSQL** | Database with pgvector | ~$15-30/month (db.t3.micro) |
| **ElastiCache Redis** | Caching and sessions | ~$15-25/month |
| **S3** | Document storage | ~$1-5/month |
| **Bedrock** | LLM (Claude) | Pay per token (~$0.001/1K tokens) |

---

### Step 1: AWS Account Setup

#### 1.1 Create IAM User for ClaimLens

```bash
# Create IAM user
aws iam create-user --user-name claimlens-app

# Create access keys
aws iam create-access-key --user-name claimlens-app
```

Save the `AccessKeyId` and `SecretAccessKey` - you'll need these later.

#### 1.2 Attach Required Policies

Create a policy file `claimlens-policy.json`:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::claimlens-documents-*",
                "arn:aws:s3:::claimlens-documents-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-*",
                "arn:aws:bedrock:*::foundation-model/amazon.titan-*"
            ]
        }
    ]
}
```

```bash
# Create and attach policy
aws iam create-policy \
    --policy-name ClaimLensAppPolicy \
    --policy-document file://claimlens-policy.json

aws iam attach-user-policy \
    --user-name claimlens-app \
    --policy-arn arn:aws:iam::<ACCOUNT_ID>:policy/ClaimLensAppPolicy
```

---

### Step 2: Set Up S3 Bucket

```bash
# Create S3 bucket (use your region)
aws s3 mb s3://claimlens-documents-<your-unique-id> --region ap-south-1

# Enable versioning (recommended)
aws s3api put-bucket-versioning \
    --bucket claimlens-documents-<your-unique-id> \
    --versioning-configuration Status=Enabled

# Set CORS for web access
aws s3api put-bucket-cors \
    --bucket claimlens-documents-<your-unique-id> \
    --cors-configuration '{
        "CORSRules": [{
            "AllowedHeaders": ["*"],
            "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
            "AllowedOrigins": ["*"],
            "ExposeHeaders": ["ETag"]
        }]
    }'
```

---

### Step 3: Set Up RDS PostgreSQL

#### 3.1 Create RDS Instance

```bash
# Create subnet group (if needed)
aws rds create-db-subnet-group \
    --db-subnet-group-name claimlens-db-subnet \
    --db-subnet-group-description "ClaimLens DB Subnet" \
    --subnet-ids subnet-xxxx subnet-yyyy

# Create security group
aws ec2 create-security-group \
    --group-name claimlens-db-sg \
    --description "ClaimLens Database Security Group"

# Allow PostgreSQL access (restrict to your IP/VPC in production)
aws ec2 authorize-security-group-ingress \
    --group-name claimlens-db-sg \
    --protocol tcp \
    --port 5432 \
    --cidr 0.0.0.0/0

# Create RDS instance
aws rds create-db-instance \
    --db-instance-identifier claimlens-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 16.1 \
    --master-username postgres \
    --master-user-password <YOUR_SECURE_PASSWORD> \
    --allocated-storage 20 \
    --storage-type gp2 \
    --vpc-security-group-ids <security-group-id> \
    --db-subnet-group-name claimlens-db-subnet \
    --publicly-accessible \
    --backup-retention-period 7
```

#### 3.2 Enable pgvector Extension

After RDS is available, connect and enable pgvector:

```bash
# Connect to RDS
psql -h <rds-endpoint> -U postgres -d postgres

# Create database and enable pgvector
CREATE DATABASE claimlens;
\c claimlens
CREATE EXTENSION IF NOT EXISTS vector;
```

#### 3.3 Get RDS Endpoint

```bash
aws rds describe-db-instances \
    --db-instance-identifier claimlens-db \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text
```

---

### Step 4: Set Up ElastiCache Redis

```bash
# Create cache subnet group
aws elasticache create-cache-subnet-group \
    --cache-subnet-group-name claimlens-redis-subnet \
    --cache-subnet-group-description "ClaimLens Redis Subnet" \
    --subnet-ids subnet-xxxx subnet-yyyy

# Create security group for Redis
aws ec2 create-security-group \
    --group-name claimlens-redis-sg \
    --description "ClaimLens Redis Security Group"

aws ec2 authorize-security-group-ingress \
    --group-name claimlens-redis-sg \
    --protocol tcp \
    --port 6379 \
    --cidr 0.0.0.0/0

# Create Redis cluster
aws elasticache create-cache-cluster \
    --cache-cluster-id claimlens-redis \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --engine-version 7.0 \
    --num-cache-nodes 1 \
    --cache-subnet-group-name claimlens-redis-subnet \
    --security-group-ids <security-group-id>
```

#### Get Redis Endpoint

```bash
aws elasticache describe-cache-clusters \
    --cache-cluster-id claimlens-redis \
    --show-cache-node-info \
    --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
    --output text
```

---

### Step 5: Enable AWS Bedrock

#### 5.1 Request Model Access

1. Go to AWS Console → Amazon Bedrock
2. Navigate to **Model access** in the left sidebar
3. Click **Manage model access**
4. Enable the following models:
   - ✅ **Anthropic Claude 3 Haiku** (recommended for cost-efficiency)
   - ✅ **Anthropic Claude 3 Sonnet** (optional, more capable)
   - ✅ **Amazon Titan Embeddings** (for vector embeddings)
5. Accept the terms and submit request

> ⏱️ Model access is usually granted within minutes, but can take up to 24 hours.

#### 5.2 Verify Model Access

```bash
# List available models
aws bedrock list-foundation-models \
    --region us-east-1 \
    --query 'modelSummaries[?contains(modelId, `claude`)].modelId'
```

---

### Step 6: Configure Environment

Edit your `.env` file with production values:

```bash
# =================================
# PRODUCTION CONFIGURATION
# =================================

ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

# =================================
# Security - CRITICAL FOR PRODUCTION
# =================================
# Generate with: openssl rand -hex 32
SECRET_KEY=<your-64-character-hex-string>
CORS_ORIGINS=https://your-domain.com

# =================================
# API Documentation Security
# =================================
# Option 1: Completely disable Swagger/OpenAPI docs
DOCS_ENABLED=false

# Option 2: Protect with basic auth (for staging/internal use)
# DOCS_ENABLED=true
# DOCS_USERNAME=admin
# DOCS_PASSWORD=<strong-password>

# Option 3: Restrict to specific IPs
# DOCS_ENABLED=true
# DOCS_ALLOWED_IPS=10.0.0.1,192.168.1.100

# =================================
# Database (AWS RDS) - SECURE PASSWORD
# =================================
DB_USER=postgres
# Generate strong password: openssl rand -base64 24
DB_PASSWORD=<your-strong-rds-password>
DB_NAME=claimlens
DB_HOST=<your-rds-endpoint>.rds.amazonaws.com
DB_PORT=5432
DATABASE_URL=postgresql+asyncpg://postgres:<password>@<rds-endpoint>:5432/claimlens

# =================================
# Redis (AWS ElastiCache) - WITH AUTH TOKEN
# =================================
# For ElastiCache with auth token enabled:
REDIS_PASSWORD=<your-redis-auth-token>
REDIS_URL=redis://:<password>@<elasticache-endpoint>:6379/0

# For ElastiCache without auth (not recommended):
# REDIS_URL=redis://<elasticache-endpoint>:6379/0

# =================================
# AWS Credentials
# =================================
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=<your-access-key>
AWS_SECRET_ACCESS_KEY=<your-secret-key>

# S3
S3_BUCKET_NAME=claimlens-documents-<your-unique-id>
USE_LOCALSTACK=false
S3_ENDPOINT_URL=
AWS_ENDPOINT_URL=

# =================================
# LLM - AWS Bedrock
# =================================
USE_MOCK_LLM=false
BEDROCK_ENABLED=true
EMBEDDING_MODE=bedrock
SKIP_MODEL_LOADING=false
BEDROCK_MODEL_ID=amazon.titan-embed-text-v1
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1
```

### Password Generation Commands

```bash
# Generate secure SECRET_KEY (64 hex characters)
openssl rand -hex 32

# Generate secure database password
openssl rand -base64 24

# Generate secure Redis auth token
openssl rand -base64 32
```

---

### Step 7: Deploy Production

#### Option A: Deploy on EC2

```bash
# SSH to your EC2 instance
ssh -i your-key.pem ec2-user@<ec2-public-ip>

# Install Docker
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone and deploy
git clone <repository-url>
cd ClaimLens-AI4Bharat

# Copy your configured .env file
nano .env  # Paste your production configuration

# Start production services
./docker-manage.sh start prod
```

#### Option B: Use CloudFormation (Automated)

```bash
# Deploy the CloudFormation stack
aws cloudformation create-stack \
    --stack-name claimlens-infrastructure \
    --template-body file://aws/cloudformation/infrastructure.yml \
    --parameters \
        ParameterKey=Environment,ParameterValue=production \
        ParameterKey=DBPassword,ParameterValue=<your-password> \
    --capabilities CAPABILITY_IAM
```

---

### Step 8: Verify Deployment

```bash
# Check container status
./docker-manage.sh status

# Check backend health
curl http://localhost:8000/health

# Check logs for errors
./docker-manage.sh logs backend
```

---

## Environment Configuration

### Complete `.env` Reference

| Variable | Local Value | Production Value | Description |
|----------|-------------|------------------|-------------|
| `ENVIRONMENT` | `local` | `production` | Environment mode |
| `DEBUG` | `true` | `false` | Enable debug mode |
| `SECRET_KEY` | `dev-secret-key...` | `<generated>` | JWT signing key |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@db:5432/claimlens` | `postgresql+asyncpg://...@<rds>:5432/claimlens` | Database connection |
| `REDIS_URL` | `redis://redis:6379/0` | `redis://<elasticache>:6379/0` | Redis connection |
| `USE_MOCK_LLM` | `true` | `false` | Use mock LLM responses |
| `BEDROCK_ENABLED` | `false` | `true` | Enable AWS Bedrock |
| `USE_LOCALSTACK` | `true` | `false` | Use LocalStack S3 |
| `AWS_ACCESS_KEY_ID` | `test` | `<your-key>` | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | `test` | `<your-secret>` | AWS credentials |

---

## Troubleshooting

### Local Issues

**Problem: Port already in use**
```bash
# Find process using port
lsof -i :8000
lsof -i :3000

# Kill process or change port
kill <PID>
```

**Problem: Docker permission denied**
```bash
# Linux: Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

**Problem: Database migration fails**
```bash
./docker-manage.sh logs db
./docker-manage.sh exec db
# Check PostgreSQL is running and accepting connections
```

### Production Issues

**Problem: Bedrock access denied**
- Verify IAM policy includes Bedrock permissions
- Check model access is approved in Bedrock console
- Verify AWS region matches your configuration

**Problem: RDS connection refused**
- Check security group allows inbound PostgreSQL (5432)
- Verify RDS is publicly accessible or in same VPC
- Test connection: `psql -h <endpoint> -U postgres`

**Problem: S3 access denied**
- Verify IAM policy includes S3 permissions
- Check bucket name matches configuration
- Test with: `aws s3 ls s3://<bucket-name>`

### Logs and Debugging

```bash
# View all logs
./docker-manage.sh logs

# View specific service logs
./docker-manage.sh logs backend
./docker-manage.sh logs frontend

# Follow logs in real-time
docker logs -f claimlens-backend

# Check container health
docker ps
./docker-manage.sh status
```

---

## Security Checklist for Production

### Authentication & Secrets
- [ ] Generate unique `SECRET_KEY` with `openssl rand -hex 32`
- [ ] Generate strong PostgreSQL password with `openssl rand -base64 24`
- [ ] Generate Redis auth token with `openssl rand -base64 32`
- [ ] Store secrets in AWS Secrets Manager (recommended)
- [ ] Never commit `.env` file to git

### API Security
- [ ] Disable Swagger docs (`DOCS_ENABLED=false`) or protect with auth
- [ ] Set `DOCS_USERNAME` and `DOCS_PASSWORD` if docs are enabled
- [ ] Restrict `DOCS_ALLOWED_IPS` to internal IPs only
- [ ] Set `CORS_ORIGINS` to your specific domain only

### Database Security
- [ ] Use strong PostgreSQL password (min 24 characters)
- [ ] Enable RDS encryption at rest
- [ ] Restrict RDS security group to application VPC only
- [ ] Enable RDS automated backups
- [ ] Enable RDS deletion protection

### Redis Security
- [ ] Enable ElastiCache auth token (Redis AUTH)
- [ ] Enable ElastiCache encryption in-transit
- [ ] Enable ElastiCache encryption at-rest
- [ ] Restrict Redis security group to application VPC only

### Network Security
- [ ] Use VPC with private subnets for RDS/Redis
- [ ] Configure HTTPS with SSL certificate (ACM)
- [ ] Use Application Load Balancer with WAF
- [ ] Restrict security groups to necessary IPs only

### AWS Security
- [ ] Use IAM roles instead of access keys when possible
- [ ] Rotate AWS access keys regularly (every 90 days)
- [ ] Enable AWS CloudTrail for audit logging
- [ ] Enable S3 bucket versioning
- [ ] Set up CloudWatch alarms for monitoring
- [ ] Enable GuardDuty for threat detection

---

## Securing ElastiCache Redis with Auth Token

### Step 1: Create Redis with Auth Token

```bash
# Create Redis cluster with auth token enabled
aws elasticache create-cache-cluster \
    --cache-cluster-id claimlens-redis \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --engine-version 7.0 \
    --num-cache-nodes 1 \
    --cache-subnet-group-name claimlens-redis-subnet \
    --security-group-ids <security-group-id> \
    --auth-token "<your-strong-auth-token>" \
    --transit-encryption-enabled \
    --at-rest-encryption-enabled
```

### Step 2: Update Environment

```bash
# In .env
REDIS_PASSWORD=<your-auth-token>
REDIS_URL=redis://:<your-auth-token>@<endpoint>:6379/0
```

### Step 3: Verify Connection

```bash
# Test Redis connection with auth
redis-cli -h <endpoint> -p 6379 --tls -a <auth-token> PING
```

---

## Securing Swagger/OpenAPI Documentation

### Option 1: Completely Disable (Recommended for Production)

```bash
# In .env
DOCS_ENABLED=false
```

### Option 2: Basic Auth Protection (For Staging)

```bash
# In .env
DOCS_ENABLED=true
DOCS_USERNAME=admin
DOCS_PASSWORD=<strong-password-here>
```

### Option 3: IP Whitelist (For Internal Use)

```bash
# In .env
DOCS_ENABLED=true
DOCS_ALLOWED_IPS=10.0.0.1,10.0.0.2,192.168.1.100
```

### Implementation Note

The backend should check these environment variables to conditionally enable/protect docs:

```python
# In backend/app/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

docs_enabled = os.getenv("DOCS_ENABLED", "true").lower() == "true"
docs_url = "/docs" if docs_enabled else None
redoc_url = "/redoc" if docs_enabled else None

app = FastAPI(docs_url=docs_url, redoc_url=redoc_url)
```

---

## Support

For issues and questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review logs: `./docker-manage.sh logs`
3. Open an issue in the repository
