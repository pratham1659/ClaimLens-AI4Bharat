# ClaimLens Docker Setup Guide

## Overview

This project uses Docker with separate configurations for **Local Development** and **Production**:

| Mode | LLM | S3 Storage | Configuration |
|------|-----|------------|---------------|
| **Local** | Mock LLM (no AWS costs) | LocalStack | `.env.sample`, `docker-compose.local.yml` |
| **Production** | AWS Bedrock | AWS S3 | `.env.prod`, `docker-compose.prod.yml` |

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- macOS, Linux, or Windows with WSL2

> **macOS with Vessel:** If you use Apple Vessel instead of Docker Desktop, use [`docker-manage-vessel.sh`](docker-manage-vessel.sh) instead.

### Local Development (Recommended for Development)

Start with Mock LLM and LocalStack (no AWS costs):

```bash
./docker-manage.sh start local
```

This will:
- Build and start all containers
- Enable hot-reload for frontend and backend
- Start LocalStack for S3 emulation
- Use Mock LLM responses (no AWS Bedrock costs)

Access points:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- LocalStack S3: http://localhost:4566

### Production Mode

Start with AWS Bedrock and real S3:

```bash
./docker-manage.sh start prod
```

⚠️ **Requires:** Valid AWS credentials in `.env.prod`

This will:
- Build optimized production images
- Connect to AWS Bedrock for LLM
- Connect to AWS S3 for storage
- Run with production settings

## Configuration Files

### Environment Files

| File | Purpose |
|------|---------|
| `.env.sample` | Local development settings (Mock LLM, LocalStack) |
| `.env.prod` | Production settings (AWS Bedrock, real S3) |
| `.env.example` | Template with all available options |

### Docker Compose Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Base configuration |
| `docker-compose.local.yml` | Local development overrides |
| `docker-compose.prod.yml` | Production overrides |

## Docker Manage Script Commands

### Basic Commands

| Command | Description |
|---------|-------------|
| `./docker-manage.sh start local` | Start in local mode (Mock LLM + LocalStack) |
| `./docker-manage.sh start prod` | Start in production mode (AWS Bedrock) |
| `./docker-manage.sh stop [--volumes]` | Stop containers (auto-backup) |
| `./docker-manage.sh restart [local\|prod]` | Restart containers (auto-backup) |
| `./docker-manage.sh status` | Show container status |
| `./docker-manage.sh logs [service]` | View logs |
| `./docker-manage.sh exec [service]` | Shell into container |
| `./docker-manage.sh help` | Show all commands |

### Database Commands

| Command | Description |
|---------|-------------|
| `./docker-manage.sh migrate` | Run Alembic migrations |
| `./docker-manage.sh seed` | Seed database with sample data |
| `./docker-manage.sh backup` | Create database backup |
| `./docker-manage.sh restore [file]` | Restore from backup |
| `./docker-manage.sh fix-postgres` | Fix postgres permissions |

### AWS/LocalStack Commands

| Command | Description |
|---------|-------------|
| `./docker-manage.sh aws-setup` | Show AWS configuration info |
| `./docker-manage.sh s3-create-bucket` | Create S3 bucket in LocalStack |
| `./docker-manage.sh s3-list` | List S3 bucket contents |

## LLM Configuration

### Local Development (Mock LLM)

When running in local mode, the backend uses a Mock LLM that:
- Returns simulated responses
- Has no AWS costs
- Is fast for development iteration
- Doesn't require AWS credentials

```yaml
# .env.sample
USE_MOCK_LLM=true
BEDROCK_ENABLED=false
```

### Production (AWS Bedrock)

For production, configure AWS Bedrock:

```yaml
# .env.prod
USE_MOCK_LLM=false
BEDROCK_ENABLED=true
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

Available Bedrock Models:
| Model | Use Case |
|-------|----------|
| `anthropic.claude-3-haiku-20240307-v1:0` | Fast, cost-effective |
| `anthropic.claude-3-sonnet-20240229-v1:0` | Balanced |
| `anthropic.claude-3-opus-20240229-v1:0` | Most capable |

## Environment Variables

### Core Variables

| Variable | Local Default | Production |
|----------|---------------|------------|
| `ENVIRONMENT` | development | production |
| `DEBUG` | true | false |
| `SECRET_KEY` | dev-key | (required) |

### LLM Variables

| Variable | Local | Production |
|----------|-------|------------|
| `USE_MOCK_LLM` | true | false |
| `BEDROCK_ENABLED` | false | true |
| `BEDROCK_MODEL_ID` | - | anthropic.claude-3-haiku... |

### AWS Variables

| Variable | Local | Production |
|----------|-------|------------|
| `AWS_REGION` | us-east-1 | (required) |
| `AWS_ACCESS_KEY_ID` | test | (required) |
| `AWS_SECRET_ACCESS_KEY` | test | (required) |
| `S3_ENDPOINT_URL` | http://localstack:4566 | (empty) |
| `USE_LOCALSTACK` | true | false |

## Services

### Backend (FastAPI)

- Python 3.11 with FastAPI
- Async SQLAlchemy with PostgreSQL
- pgvector for embeddings
- Hot-reload in local mode

### Frontend (React/Vite)

- React 18 with Vite
- Hot-reload in local mode
- Nginx in production

### Database (PostgreSQL + pgvector)

- PostgreSQL 16 with pgvector extension
- Vector search for document embeddings

### LocalStack (Local only)

- S3 emulation for local development
- No AWS costs during development

## Backup & Restore

### Automatic Backups

Backups are automatically created before:
- Stopping containers
- Restarting containers
- Cleaning containers

### Manual Backup

```bash
./docker-manage.sh backup
```

### Restore from Backup

```bash
# Interactive restore (shows available backups)
./docker-manage.sh restore

# Auto restore from latest backup
./docker-manage.sh restore --auto

# Restore specific backup
./docker-manage.sh restore ./backups/claimlens_backup_20240315_120000.sql
```

## Troubleshooting

### Containers not starting

1. Check Docker is running
2. Check logs: `./docker-manage.sh logs`
3. Ensure ports are not in use (3000, 8000, 5432, 6379, 4566)

### LLM not responding

**Local mode:**
- Verify `USE_MOCK_LLM=true` in `.env.sample`
- Check backend logs for errors

**Production mode:**
- Verify AWS credentials are correct
- Check Bedrock model access is enabled in AWS console
- Review backend logs: `./docker-manage.sh logs backend`

### LocalStack issues

1. Check LocalStack logs: `./docker-manage.sh logs localstack`
2. Verify S3 bucket exists: `./docker-manage.sh s3-list`
3. Create bucket: `./docker-manage.sh s3-create-bucket`

### Database issues

1. Check PostgreSQL logs: `./docker-manage.sh logs db`
2. Run migrations: `./docker-manage.sh migrate`
3. Fix permissions: `./docker-manage.sh fix-postgres`

### Clean restart

```bash
# Stop and remove all data
./docker-manage.sh clean

# Start fresh in local mode
./docker-manage.sh start local
```

## AWS Production Deployment

For AWS deployment:

1. Copy `.env.prod` and update with production values
2. Configure S3 bucket in AWS
3. Enable Bedrock model access in AWS console
4. Use CloudFormation template in `aws/cloudformation/`
5. Deploy with: `./docker-manage.sh start prod`

See `aws/cloudformation/infrastructure.yml` for the AWS infrastructure template.
