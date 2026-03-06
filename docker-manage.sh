#!/bin/bash

# ClaimLens Insurance Docker Management Script
# Unified script to start, stop, restart, and manage Docker containers
# Usage: ./docker-manage.sh [command] [options]

set -e

# Project configuration
PROJECT_NAME="ClaimLens"
CONTAINER_PREFIX="claimlens"

# Function to show help
show_help() {
    echo "🐳 $PROJECT_NAME Docker Management Script"
    echo "============================================"
    echo ""
    echo "Usage: ./docker-manage.sh [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start [local|prod]      - Start the application containers"
    echo "  stop [--volumes]        - Stop the application containers (auto-backup)"
    echo "  restart [local|prod]    - Restart the application containers (auto-backup)"
    echo "  status                  - Show status of all containers"
    echo "  logs [service]          - View logs (optional: specific service)"
    echo "  exec [service]          - Execute bash in a service container"
    echo "  migrate                 - Run database migrations"
    echo "  seed                    - Seed database with sample data"
    echo "  backup                  - Backup the database manually"
    echo "  scheduled-backup        - Backup the database (for cron jobs)"
    echo "  restore [backup_file]   - Restore database from backup"
    echo "  restore --auto          - Restore from latest backup (non-interactive)"
    echo "  fix-postgres            - Create postgres user and grant permissions"
    echo "  clean                   - Stop containers and remove volumes (auto-backup)"
    echo "  help                    - Show this help message"
    echo ""
    echo "AWS Commands:"
    echo "  aws-setup               - Show AWS configuration info"
    echo "  s3-create-bucket        - Create S3 bucket in LocalStack"
    echo "  s3-list                 - List files in S3 bucket"
    echo ""
    echo "Modes:"
    echo "  local      - Local development with LocalStack & Mock LLM"
    echo "               Features: Hot-reload, LocalStack S3, Mock AI responses"
    echo "               Services: db, redis, localstack, backend-local, frontend-local"
    echo ""
    echo "  prod       - Production mode with AWS Bedrock"
    echo "               Features: AWS Bedrock LLM, production S3, optimized builds"
    echo "               Services: backend-prod, frontend-prod (external db/redis)"
    echo ""
    echo "Options:"
    echo "  --volumes  - Also remove volumes when stopping"
    echo ""
    echo "Environment:"
    echo "  .env.sample - Template configuration file"
    echo "  .env        - Active configuration (copy from .env.sample)"
    echo ""
    echo "Examples:"
    echo "  ./docker-manage.sh start local       # Local dev with Mock LLM + LocalStack"
    echo "  ./docker-manage.sh start prod        # Production with AWS Bedrock"
    echo "  ./docker-manage.sh stop              # Stop containers (auto-backup)"
    echo "  ./docker-manage.sh logs backend      # View backend logs"
    echo "  ./docker-manage.sh migrate           # Run migrations"
    echo ""
    exit 0
}

# Function to determine docker compose command
get_docker_compose_cmd() {
    if docker compose version &> /dev/null; then
        echo "docker compose"
    elif command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    else
        echo "❌ Neither 'docker compose' nor 'docker-compose' is available"
        echo ""
        echo "Please install Docker Compose:"
        echo "  macOS: brew install docker-compose"
        echo "  Linux: sudo apt-get install docker-compose-plugin"
        exit 1
    fi
}

# Function to verify docker daemon access
check_docker_access() {
    if docker info > /dev/null 2>&1; then
        return 0
    fi

    local docker_error
    docker_error=$(docker info 2>&1 || true)

    echo "❌ Cannot access Docker daemon"
    echo ""

    if echo "$docker_error" | grep -qiE "permission denied|/var/run/docker.sock"; then
        echo "   Your user doesn't have permission to access Docker."
        echo ""
        echo "   Linux fix:"
        echo "   1) sudo usermod -aG docker \$USER"
        echo "   2) newgrp docker"
        echo "   3) ./docker-manage.sh start local"
    else
        echo "   Docker may not be running."
        echo ""
        echo "   Try:"
        echo "   1) sudo systemctl start docker"
        echo "   2) ./docker-manage.sh start local"
    fi

    exit 1
}

# Function to check if a TCP port is in use
is_port_in_use() {
    local port=$1

    if command -v ss &> /dev/null; then
        ss -ltn 2>/dev/null | awk '{print $4}' | grep -E "(^|:)${port}$" > /dev/null
        return $?
    fi

    if command -v lsof &> /dev/null; then
        lsof -iTCP:"$port" -sTCP:LISTEN -n -P > /dev/null 2>&1
        return $?
    fi

    return 1
}

# Function to resolve Redis port conflicts
resolve_redis_port_conflict() {
    local mode=$1
    local configured_port=${REDIS_HOST_PORT:-6379}

    if ! is_port_in_use "$configured_port"; then
        export REDIS_HOST_PORT="$configured_port"
        echo "🔌 Redis host port: $REDIS_HOST_PORT"
        return 0
    fi

    if [[ -n "${REDIS_HOST_PORT+x}" ]]; then
        echo "❌ Redis host port $configured_port is already in use"
        echo "   Set REDIS_HOST_PORT to a free port and retry"
        exit 1
    fi

    if [[ "$mode" == "local" ]]; then
        for fallback_port in $(seq 6380 6399); do
            if ! is_port_in_use "$fallback_port"; then
                export REDIS_HOST_PORT="$fallback_port"
                echo "⚠️  Port 6379 is busy; using Redis host port $REDIS_HOST_PORT"
                return 0
            fi
        done

        echo "❌ Could not find a free Redis host port in range 6380-6399"
        exit 1
    fi

    echo "❌ Redis host port 6379 is already in use"
    exit 1
}

# Function to ensure .env file exists
ensure_env_file() {
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env.sample" ]]; then
            echo "📋 Creating .env from .env.sample..."
            cp .env.sample .env
        else
            echo "❌ No .env or .env.sample file found"
            echo "   Please create .env.sample first"
            exit 1
        fi
    fi
}

# Function to load environment variables
load_env() {
    ensure_env_file
    
    if [[ -f ".env" ]]; then
        echo "📋 Loading .env configuration..."
        set -a
        source .env
        set +a
    fi
}

# Function to start containers
start_containers() {
    echo "🐳 $PROJECT_NAME Docker Service Management Script"
    echo "===================================================="
    
    local MODE="local"
    local PROFILE="local"
    
    if [[ "$1" == "local" || "$1" == "dev" || "$1" == "development" || -z "$1" ]]; then
        MODE="local"
        PROFILE="local"
        echo "📋 Mode: Local Development"
        echo "   ✨ Features:"
        echo "      - Hot-reload enabled"
        echo "      - LocalStack for S3 emulation"
        echo "      - Mock LLM responses (no AWS costs)"
        echo "      - Debug mode enabled"
    elif [[ "$1" == "prod" || "$1" == "production" ]]; then
        MODE="prod"
        PROFILE="prod"
        echo "📋 Mode: Production"
        echo "   🔒 Features:"
        echo "      - AWS Bedrock for LLM"
        echo "      - AWS S3 for storage"
        echo "      - External DB/Redis (AWS RDS/ElastiCache)"
        echo "      - Optimized builds"
    else
        echo "❌ Invalid mode: $1"
        echo ""
        echo "Available modes: local, prod"
        show_help
    fi
    
    # Load environment variables
    load_env
    
    # Get docker compose command
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    echo "📦 Using: $DOCKER_COMPOSE_CMD"

    # Check docker daemon access
    check_docker_access

    # Resolve Redis port conflicts for local mode
    if [[ "$MODE" == "local" ]]; then
        resolve_redis_port_conflict "$MODE"
    fi
    
    echo ""
    echo "🚀 Building and starting services..."
    echo "   This may take a few minutes on first run..."
    
    # Start with the appropriate profile
    DOCKER_BUILDKIT=1 $DOCKER_COMPOSE_CMD --profile "$PROFILE" up -d --build
    
    echo ""
    echo "⏳ Waiting for services to be healthy..."
    sleep 10
    
    # Health checks based on mode
    if [[ "$MODE" == "local" ]]; then
        # Wait for postgres
        echo "🔍 Checking PostgreSQL health..."
        local max_retries=30
        local retry_count=0
        while [ $retry_count -lt $max_retries ]; do
            if $DOCKER_COMPOSE_CMD --profile "$PROFILE" exec -T db pg_isready -U ${DB_USER:-postgres} &> /dev/null; then
                echo "✅ PostgreSQL is ready"
                break
            fi
            retry_count=$((retry_count + 1))
            echo "   Waiting for PostgreSQL... ($retry_count/$max_retries)"
            sleep 2
        done
        
        # Wait for Redis
        echo ""
        echo "🔍 Checking Redis health..."
        retry_count=0
        while [ $retry_count -lt $max_retries ]; do
            if $DOCKER_COMPOSE_CMD --profile "$PROFILE" exec -T redis redis-cli ping &> /dev/null; then
                echo "✅ Redis is ready"
                break
            fi
            retry_count=$((retry_count + 1))
            echo "   Waiting for Redis... ($retry_count/$max_retries)"
            sleep 2
        done
        
        # Wait for LocalStack
        echo ""
        echo "🔍 Checking LocalStack health..."
        retry_count=0
        local max_localstack_retries=15
        while [ $retry_count -lt $max_localstack_retries ]; do
            if curl -sf http://localhost:4566/_localstack/health &> /dev/null; then
                echo "✅ LocalStack is ready"
                break
            fi
            retry_count=$((retry_count + 1))
            echo "   Waiting for LocalStack... ($retry_count/$max_localstack_retries)"
            sleep 2
        done
    else
        # Production - check backend health
        echo "🔍 Checking Backend health..."
        local retry_count=0
        local max_retries=30
        while [ $retry_count -lt $max_retries ]; do
            if curl -sf http://localhost:8000/health &> /dev/null; then
                echo "✅ Backend is ready"
                break
            fi
            retry_count=$((retry_count + 1))
            echo "   Waiting for Backend... ($retry_count/$max_retries)"
            sleep 2
        done
    fi
    
    # Run database migrations (local mode only)
    if [[ "$MODE" == "local" ]]; then
        echo ""
        echo "📊 Running database migrations..."
        if $DOCKER_COMPOSE_CMD --profile "$PROFILE" exec -T ${CONTAINER_PREFIX}-backend alembic upgrade head 2>/dev/null; then
            echo "✅ Database migrations completed"
        else
            echo "⚠️  Could not run migrations (backend may still be starting)"
            echo "   Run manually: ./docker-manage.sh migrate"
        fi
    fi
    
    # Show status
    echo ""
    echo "📊 Service Status:"
    $DOCKER_COMPOSE_CMD --profile "$PROFILE" ps
    
    echo ""
    echo "✅ Services started successfully in $MODE mode"
    
    echo ""
    echo "🌐 Access Points:"
    if [[ "$MODE" == "local" ]]; then
        echo "   - Frontend (Dev):      http://localhost:3000"
        echo "   - Backend API:         http://localhost:8000"
        echo "   - Swagger Docs:        http://localhost:8000/docs"
        echo "   - Health Check:        http://localhost:8000/health"
        echo "   - LocalStack S3:       http://localhost:4566"
        echo "   - PostgreSQL:          localhost:5432"
        echo "   - Redis:               localhost:${REDIS_HOST_PORT:-6379}"
        echo ""
        echo "🤖 LLM: Mock LLM (no AWS costs)"
    else
        echo "   - Frontend:            http://localhost:80"
        echo "   - Backend API:         http://localhost:8000"
        echo "   - Swagger Docs:        http://localhost:8000/docs"
        echo ""
        echo "🤖 LLM: AWS Bedrock (${BEDROCK_MODEL_ID:-anthropic.claude-3-haiku-20240307-v1:0})"
    fi
    
    echo ""
    echo "📋 Useful Commands:"
    echo "   - View logs: ./docker-manage.sh logs"
    echo "   - Check status: ./docker-manage.sh status"
    echo "   - Stop services: ./docker-manage.sh stop"
}

# Function to stop containers
stop_containers() {
    echo "🛑 $PROJECT_NAME Docker Service Stop Script"
    echo "=============================================="
    
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    
    # Auto-backup before stopping
    auto_backup_before_stop
    
    if [[ "$1" == "--volumes" ]]; then
        echo "📋 Mode: Stop and remove volumes"
        echo ""
        echo "🛑 Stopping services and removing volumes..."
        $DOCKER_COMPOSE_CMD --profile local --profile prod down -v --remove-orphans
        echo "✅ Services stopped and volumes removed"
    else
        echo "📋 Mode: Stop services (preserve data)"
        echo ""
        echo "🛑 Stopping services..."
        $DOCKER_COMPOSE_CMD --profile local --profile prod down --remove-orphans
        echo "✅ Services stopped (volumes preserved)"
    fi
}

# Function to restart containers
restart_containers() {
    echo "🔄 $PROJECT_NAME Docker Service Restart Script"
    echo "================================================="
    
    local MODE="local"
    
    if [[ "$1" == "prod" || "$1" == "production" ]]; then
        MODE="prod"
    fi
    
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    
    # Auto-backup before restarting
    auto_backup_before_stop
    
    echo "🛑 Stopping existing services..."
    $DOCKER_COMPOSE_CMD --profile local --profile prod down --remove-orphans 2>/dev/null || true
    
    # Start with the specified mode
    start_containers "$MODE"
}

# Function to show status
show_status() {
    echo "🐳 $PROJECT_NAME Docker Status"
    echo "================================="
    
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    
    echo ""
    echo "📊 Container Status:"
    $DOCKER_COMPOSE_CMD --profile local --profile prod ps
    
    echo ""
    echo "📈 Container Resource Usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
        $(docker ps --format '{{.Names}}' | grep $CONTAINER_PREFIX) 2>/dev/null || \
        echo "No $PROJECT_NAME containers running"
}

# Function to view logs
view_logs() {
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    
    SERVICE=$1
    
    if [[ -z "$SERVICE" ]]; then
        echo "📋 Viewing all logs (Ctrl+C to exit)..."
        $DOCKER_COMPOSE_CMD --profile local --profile prod logs -f
    else
        echo "📋 Viewing logs for: $SERVICE (Ctrl+C to exit)..."
        docker logs -f "${CONTAINER_PREFIX}-${SERVICE}" 2>/dev/null || \
            $DOCKER_COMPOSE_CMD --profile local --profile prod logs -f "$SERVICE"
    fi
}

# Function to execute bash in container
exec_container() {
    SERVICE=${1:-backend}
    CONTAINER_NAME="${CONTAINER_PREFIX}-${SERVICE}"
    
    echo "💻 Opening shell in: $SERVICE"
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        if [[ "$SERVICE" == "db" ]]; then
            DB_NAME=${DB_NAME:-claimlens}
            DB_USER=${DB_USER:-postgres}
            docker exec -it "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME"
        elif [[ "$SERVICE" == "redis" ]]; then
            docker exec -it "$CONTAINER_NAME" redis-cli
        else
            docker exec -it "$CONTAINER_NAME" bash 2>/dev/null || docker exec -it "$CONTAINER_NAME" sh
        fi
    else
        echo "❌ Container $CONTAINER_NAME is not running"
        echo "   Start the application first: ./docker-manage.sh start"
        exit 1
    fi
}

# Function to run migrations
run_migrations() {
    echo "📊 Running database migrations..."
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-backend$"; then
        docker exec -it ${CONTAINER_PREFIX}-backend alembic upgrade head
        echo "✅ Migrations completed"
    else
        echo "❌ Backend container is not running"
        echo "   Start the application first: ./docker-manage.sh start"
        exit 1
    fi
}

# Function to seed database
seed_database() {
    echo "🌱 Seeding database with sample data..."
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-backend$"; then
        docker exec -it ${CONTAINER_PREFIX}-backend python -m scripts.seed_data 2>/dev/null || \
        docker exec -it ${CONTAINER_PREFIX}-backend python scripts/seed_data.py
        echo "✅ Database seeded successfully"
    else
        echo "❌ Backend container is not running"
        exit 1
    fi
}

# Function to backup database
backup_database() {
    BACKUP_DIR="./backups"
    mkdir -p "$BACKUP_DIR"
    
    echo "💾 Backing up database..."
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-db$"; then
        DB_NAME=${DB_NAME:-claimlens}
        DB_USER=${DB_USER:-postgres}
        
        # Check if database has data
        HAS_DATA=$(docker exec ${CONTAINER_PREFIX}-db psql -U "$DB_USER" -d "$DB_NAME" -t -c \
            "SELECT COUNT(*) FROM (SELECT 1 FROM information_schema.tables t WHERE t.table_schema = 'public' LIMIT 1) AS has_data;" 2>/dev/null || echo "0")
        HAS_DATA=$(echo "$HAS_DATA" | tr -d '[:space:]')
        
        if [ "$HAS_DATA" -eq "0" ] 2>/dev/null; then
            echo "⚠️  Database appears to be empty - skipping backup"
            return 0
        fi
        
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_FILE="${BACKUP_DIR}/${CONTAINER_PREFIX}_backup_${TIMESTAMP}.sql"
        
        docker exec ${CONTAINER_PREFIX}-db pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc -Z 9 -f "/tmp/backup.dump"
        docker cp ${CONTAINER_PREFIX}-db:/tmp/backup.dump "$BACKUP_FILE"
        
        if [ -f "$BACKUP_FILE" ]; then
            FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
            echo "✅ Database backed up: $BACKUP_FILE ($FILE_SIZE)"
        fi
        
        # Keep only last 10 backups
        cd "$BACKUP_DIR"
        ls -t ${CONTAINER_PREFIX}_backup_*.sql 2>/dev/null | tail -n +11 | xargs -r rm -- 2>/dev/null || true
        cd - > /dev/null
    else
        echo "⚠️  PostgreSQL container is not running - skipping backup"
        return 1
    fi
}

# Function to auto-backup before stopping
auto_backup_before_stop() {
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-db$"; then
        echo "🔒 Auto-backup before stopping..."
        backup_database
        echo ""
    fi
}

# Function to restore database
restore_database() {
    BACKUP_DIR="./backups"
    
    echo "🔄 Restoring database from backup..."
    
    if [[ ! -d "$BACKUP_DIR" ]]; then
        echo "❌ Backup directory not found: $BACKUP_DIR"
        exit 1
    fi
    
    AUTO_MODE=false
    if [[ "$1" == "--auto" ]]; then
        AUTO_MODE=true
        BACKUP_FILE=$(ls -t "$BACKUP_DIR"/${CONTAINER_PREFIX}_backup_*.sql 2>/dev/null | head -n 1)
        
        if [[ -z "$BACKUP_FILE" ]]; then
            echo "❌ No backup files found"
            exit 1
        fi
        echo "Using latest backup: $BACKUP_FILE"
    elif [[ -n "$1" && "$1" != "--auto" ]]; then
        BACKUP_FILE="$1"
        if [[ ! -f "$BACKUP_FILE" ]]; then
            echo "❌ Backup file not found: $BACKUP_FILE"
            exit 1
        fi
    else
        echo "📁 Available backups:"
        ls -lht "$BACKUP_DIR"/${CONTAINER_PREFIX}_backup_*.sql 2>/dev/null | awk '{print NR". "$9" ("$5")"}'
        BACKUP_FILE=$(ls -t "$BACKUP_DIR"/${CONTAINER_PREFIX}_backup_*.sql 2>/dev/null | head -n 1)
        echo ""
        echo "Using latest backup: $BACKUP_FILE"
    fi
    
    echo ""
    echo "⚠️  WARNING: This will replace ALL current database data!"
    
    if [[ "$AUTO_MODE" != "true" ]]; then
        read -p "Are you sure? (yes/no): " -r
        if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
            echo "❌ Restore cancelled"
            exit 0
        fi
    fi
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-db$"; then
        echo "❌ PostgreSQL container is not running"
        exit 1
    fi
    
    DB_NAME=${DB_NAME:-claimlens}
    DB_USER=${DB_USER:-postgres}
    
    docker cp "$BACKUP_FILE" ${CONTAINER_PREFIX}-db:/tmp/restore.dump
    docker exec ${CONTAINER_PREFIX}-db psql -U "$DB_USER" -d postgres -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" 2>/dev/null || true
    docker exec ${CONTAINER_PREFIX}-db psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null
    docker exec ${CONTAINER_PREFIX}-db psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null
    docker exec ${CONTAINER_PREFIX}-db pg_restore -U "$DB_USER" -d "$DB_NAME" /tmp/restore.dump 2>/dev/null || \
        docker exec -i ${CONTAINER_PREFIX}-db psql -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE"
    
    echo "✅ Database restored from: $BACKUP_FILE"
    
    if [[ "$AUTO_MODE" == "true" ]]; then
        docker restart ${CONTAINER_PREFIX}-backend
        echo "✅ Backend restarted"
    fi
}

# Function to clean everything
clean_all() {
    echo "🧹 $PROJECT_NAME Docker Clean Script"
    echo "======================================="
    echo ""
    echo "⚠️  WARNING: This will stop all containers and remove all data!"
    read -p "Are you sure? (yes/no): " -r
    
    if [[ $REPLY =~ ^[Yy]es$ ]]; then
        DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
        
        auto_backup_before_stop
        
        echo "🧹 Cleaning up..."
        $DOCKER_COMPOSE_CMD --profile local --profile prod down -v --remove-orphans
        echo "✅ Cleanup completed"
    else
        echo "❌ Cleanup cancelled"
    fi
}

# Function for scheduled backups
scheduled_backup() {
    LOGS_DIR="./logs"
    mkdir -p "$LOGS_DIR"
    LOG_FILE="$LOGS_DIR/backup.log"
    
    echo "$(date): Starting scheduled backup..." >> "$LOG_FILE"
    
    if ! docker info > /dev/null 2>&1; then
        echo "$(date): Docker is not running, skipping backup" >> "$LOG_FILE"
        exit 0
    fi
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-db$"; then
        echo "$(date): PostgreSQL container is not running, skipping backup" >> "$LOG_FILE"
        exit 0
    fi
    
    {
        echo "$(date): Running database backup..."
        backup_database
        echo "$(date): Scheduled backup completed"
    } >> "$LOG_FILE" 2>&1
}

# Function to fix postgres permissions
fix_postgres() {
    DB_NAME=${DB_NAME:-claimlens}
    DB_USER=${DB_USER:-postgres}
    
    echo "🔧 Fixing postgres for database: $DB_NAME"
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-db$"; then
        echo "❌ PostgreSQL container is not running"
        exit 1
    fi
    
    docker exec ${CONTAINER_PREFIX}-db psql -U "$DB_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true
    
    echo "✅ Postgres setup completed"
    echo ""
    echo "🔍 Connection details:"
    echo "   - Host: localhost:5432"
    echo "   - Database: $DB_NAME"
    echo "   - User: $DB_USER"
}

# AWS/LocalStack Management Functions
aws_setup() {
    echo "🔧 AWS Configuration Setup"
    echo "==========================="
    echo ""
    echo "📋 Configuration File: .env"
    echo ""
    
    if [[ -f ".env" ]]; then
        source .env 2>/dev/null || true
        echo "   Environment: ${ENVIRONMENT:-not set}"
        echo "   AWS_REGION: ${AWS_REGION:-not set}"
        echo "   BEDROCK_ENABLED: ${BEDROCK_ENABLED:-false}"
        echo "   USE_LOCALSTACK: ${USE_LOCALSTACK:-true}"
    else
        echo "   ❌ .env not found"
        echo "   Copy .env.sample to .env and configure"
    fi
    
    echo ""
    echo "📋 Available LLM Models (AWS Bedrock):"
    echo "   - anthropic.claude-3-haiku-20240307-v1:0 (fast)"
    echo "   - anthropic.claude-3-sonnet-20240229-v1:0 (balanced)"
    echo "   - anthropic.claude-3-opus-20240229-v1:0 (most capable)"
}

s3_create_bucket() {
    echo "📦 Creating S3 bucket in LocalStack..."
    
    BUCKET_NAME=${S3_BUCKET_NAME:-claimlens-documents}
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-localstack$"; then
        echo "❌ LocalStack is not running"
        echo "   Start with: ./docker-manage.sh start local"
        exit 1
    fi
    
    docker exec ${CONTAINER_PREFIX}-localstack awslocal s3 mb s3://${BUCKET_NAME} 2>/dev/null || true
    echo "✅ S3 bucket created: $BUCKET_NAME"
}

s3_list() {
    echo "📦 Listing S3 bucket contents..."
    
    BUCKET_NAME=${S3_BUCKET_NAME:-claimlens-documents}
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-localstack$"; then
        echo "❌ LocalStack is not running"
        exit 1
    fi
    
    docker exec ${CONTAINER_PREFIX}-localstack awslocal s3 ls s3://${BUCKET_NAME}/ --recursive 2>/dev/null || \
        echo "Bucket is empty or doesn't exist"
}

# Main script logic
if [[ $# -eq 0 ]]; then
    show_help
fi

COMMAND=$1
shift

case "$COMMAND" in
    start)
        start_containers "$@"
        ;;
    stop)
        stop_containers "$@"
        ;;
    restart)
        restart_containers "$@"
        ;;
    status)
        show_status
        ;;
    logs)
        view_logs "$@"
        ;;
    exec)
        exec_container "$@"
        ;;
    migrate)
        run_migrations
        ;;
    seed)
        seed_database
        ;;
    backup)
        backup_database
        ;;
    scheduled-backup)
        scheduled_backup
        ;;
    restore)
        restore_database "$@"
        ;;
    fix-postgres)
        fix_postgres
        ;;
    clean)
        clean_all
        ;;
    aws-setup)
        aws_setup
        ;;
    s3-create-bucket)
        s3_create_bucket
        ;;
    s3-list)
        s3_list
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ Unknown command: $COMMAND"
        show_help
        ;;
esac
