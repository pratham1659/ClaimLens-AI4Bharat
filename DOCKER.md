# ClaimLens Docker Setup Guide

## Overview

ClaimLens uses a **unified Docker setup** with two modes:

| Mode | LLM | Storage | Services |
|------|-----|---------|----------|
| **Local** | Mock LLM (no AWS costs) | LocalStack S3 | db, redis, localstack, backend, frontend |
| **Prod** | AWS Bedrock | AWS S3 | backend, frontend (external db/redis) |

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- macOS, Linux, or Windows with WSL2

### 1. Setup Environment

```bash
# Copy the sample environment file
cp .env.sample .env

# Edit .env for your configuration (optional for local development)
```

### 2. Start Local Development

```bash
./docker-manage.sh start local
```

This will:
- Build and start all containers with hot-reload
- Start LocalStack for S3 emulation
- Use Mock LLM responses (no AWS costs)
- Enable debug mode

**Access points:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- LocalStack S3: http://localhost:4566

### 3. Start Production Mode

```bash
./docker-manage.sh start prod
```

**⚠️ Requires:** Valid AWS credentials in `.env`

This will:
- Build optimized production images
- Connect to AWS Bedrock for LLM
- Connect to AWS S3 for storage
- Use external database and Redis (AWS RDS/ElastiCache)

## Configuration

### Single Configuration File: `.env`

Copy `.env.sample` to `.env` and configure:

```bash
# Local development (default)
ENVIRONMENT=local
USE_MOCK_LLM=true
BEDROCK_ENABLED=false
USE_LOCALSTACK=true

# Production - set these values:
# ENVIRONMENT=production
# USE_MOCK_LLM=false
# BEDROCK_ENABLED=true
# USE_LOCALSTACK=false
# AWS_ACCESS_KEY_ID=<your-key>
# AWS_SECRET_ACCESS_KEY=<your-secret>
# DATABASE_URL=postgresql+asyncpg://...
# REDIS_URL=redis://...
```

### Key Environment Variables

| Variable | Local Default | Production |
|----------|---------------|------------|
| `ENVIRONMENT` | local | production |
| `DEBUG` | true | false |
| `USE_MOCK_LLM` | true | false |
| `BEDROCK_ENABLED` | false | true |
| `USE_LOCALSTACK` | true | false |
| `DATABASE_URL` | Local PostgreSQL | AWS RDS |
| `REDIS_URL` | Local Redis | AWS ElastiCache |

## Docker Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Unified compose with profiles |
| `backend/Dockerfile` | Multi-stage backend (local/prod targets) |
| `frontend/Dockerfile` | Multi-stage frontend (local/prod targets) |
| `.env.sample` | Template configuration |
| `docker-manage.sh` | Management script |

## Management Script Commands

### Basic Commands

```bash
./docker-manage.sh start local    # Start in local mode
./docker-manage.sh start prod     # Start in production mode
./docker-manage.sh stop           # Stop containers (auto-backup)
./docker-manage.sh stop --volumes # Stop and remove data
./docker-manage.sh restart local  # Restart in local mode
./docker-manage.sh status         # Show container status
./docker-manage.sh logs           # View all logs
./docker-manage.sh logs backend   # View backend logs
./docker-manage.sh exec backend   # Shell into backend
./docker-manage.sh exec db        # PostgreSQL shell
```

### Database Commands

```bash
./docker-manage.sh migrate        # Run Alembic migrations
./docker-manage.sh seed           # Seed sample data
./docker-manage.sh backup         # Manual database backup
./docker-manage.sh restore        # Restore from backup
./docker-manage.sh fix-postgres   # Fix postgres permissions
```

### AWS/LocalStack Commands

```bash
./docker-manage.sh aws-setup      # Show AWS configuration
./docker-manage.sh s3-create-bucket # Create S3 bucket in LocalStack
./docker-manage.sh s3-list        # List S3 bucket contents
```

## LLM Configuration

### Local Mode (Mock LLM)

- Returns simulated responses
- No AWS costs during development
- Fast iteration for UI/UX work
- No AWS credentials required

```bash
USE_MOCK_LLM=true
BEDROCK_ENABLED=false
EMBEDDING_MODE=mock
```

### Production Mode (AWS Bedrock)

Available models:
| Model | Use Case |
|-------|----------|
| `anthropic.claude-3-haiku-20240307-v1:0` | Fast, cost-effective |
| `anthropic.claude-3-sonnet-20240229-v1:0` | Balanced |
| `anthropic.claude-3-opus-20240229-v1:0` | Most capable |

```bash
USE_MOCK_LLM=false
BEDROCK_ENABLED=true
EMBEDDING_MODE=bedrock
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
```

## Architecture

### Local Mode Services

```
┌─────────────────────────────────────────────────┐
│                  Local Mode                      │
├─────────────────────────────────────────────────┤
│  frontend-local (React dev server :3000)        │
│       ↓                                          │
│  backend-local (FastAPI with hot-reload :8000)  │
│       ↓                                          │
│  ┌──────────┐  ┌───────┐  ┌────────────┐       │
│  │    db    │  │ redis │  │ localstack │        │
│  │ pgvector │  │       │  │    S3      │        │
│  └──────────┘  └───────┘  └────────────┘       │
└─────────────────────────────────────────────────┘
```

### Production Mode Services

```
┌─────────────────────────────────────────────────┐
│                Production Mode                   │
├─────────────────────────────────────────────────┤
│  frontend-prod (nginx :80)                       │
│       ↓                                          │
│  backend-prod (FastAPI optimized :8000)         │
│       ↓                                          │
│  ┌──────────────────────────────────────────┐   │
│  │              AWS Services                 │   │
│  │  RDS (PostgreSQL)  │  ElastiCache (Redis)│   │
│  │  S3 Storage        │  Bedrock LLM        │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## Backup & Restore

### Automatic Backups

Backups are automatically created before:
- Stopping containers
- Restarting containers
- Cleaning containers

### Manual Operations

```bash
# Create backup
./docker-manage.sh backup

# List and restore from backup
./docker-manage.sh restore

# Auto-restore from latest
./docker-manage.sh restore --auto
```

Backups are stored in `./backups/` (last 10 kept automatically).

## Troubleshooting

### Containers not starting

```bash
# Check Docker is running
docker info

# Check logs
./docker-manage.sh logs

# Check port conflicts (3000, 8000, 5432, 6379, 4566)
lsof -i :8000
```

### LLM not responding

**Local mode:**
- Verify `USE_MOCK_LLM=true` in `.env`
- Check: `./docker-manage.sh logs backend`

**Production mode:**
- Verify AWS credentials are correct
- Check Bedrock model access in AWS console
- Review: `./docker-manage.sh logs backend`

### Database issues

```bash
# Check PostgreSQL logs
./docker-manage.sh logs db

# Run migrations
./docker-manage.sh migrate

# Fix permissions
./docker-manage.sh fix-postgres
```

### Clean restart

```bash
# Full cleanup (removes all data)
./docker-manage.sh clean

# Start fresh
./docker-manage.sh start local
```

## AWS Production Deployment

1. Copy and configure `.env`:
   ```bash
   cp .env.sample .env
   # Set ENVIRONMENT=production and AWS credentials
   ```

2. Configure AWS services:
   - Create S3 bucket
   - Set up RDS PostgreSQL with pgvector
   - Configure ElastiCache Redis
   - Enable Bedrock model access

3. Deploy:
   ```bash
   ./docker-manage.sh start prod
   ```

See `aws/cloudformation/infrastructure.yml` for AWS infrastructure template.
