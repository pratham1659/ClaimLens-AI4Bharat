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
    echo "  scheduled-backup        - Backup the database (for cron jobs, logs to logs/backup.log)"
    echo "  restore [backup_file]   - Restore database from backup"
    echo "  restore --auto          - Restore from latest backup and auto-restart services (non-interactive)"
    echo "  fix-postgres            - Create postgres user and grant permissions for psql/pgAdmin access"
    echo "  clean                   - Stop containers and remove volumes (auto-backup)"
    echo "  help                    - Show this help message"
    echo ""
    echo "AWS Commands:"
    echo "  aws-setup               - Setup AWS credentials and configuration"
    echo "  s3-create-bucket        - Create S3 bucket in LocalStack"
    echo "  s3-list                 - List files in S3 bucket"
    echo ""
    echo "Modes:"
    echo "  local      - Local development with LocalStack & Mock LLM"
    echo "               Uses: .env.sample, docker-compose.local.yml"
    echo "               Features: Hot-reload, LocalStack S3, Mock AI responses"
    echo ""
    echo "  prod       - Production mode with AWS Bedrock"
    echo "               Uses: .env.prod, docker-compose.prod.yml"
    echo "               Features: AWS Bedrock LLM, production S3, optimized builds"
    echo "               Production URL: https://claimlen.com"
    echo "               API Docs: https://claimlen.com/docs"
    echo ""
    echo "Options:"
    echo "  --volumes  - Also remove volumes when stopping"
    echo ""
    echo "Environment Files:"
    echo "  .env.sample  - Local development configuration (Mock LLM, LocalStack)"
    echo "  .env.prod   - Production configuration (AWS Bedrock, real S3)"
    echo ""
    echo "Backup Features:"
    echo "  ✅ Auto-backup before stop, restart, and clean operations"
    echo "  ✅ Keeps last 10 backups automatically"
    echo "  ✅ Backups stored in ./backups directory"
    echo "  ✅ Restore from any backup file"
    echo ""
    echo "Examples:"
    echo "  ./docker-manage.sh start local       # Local dev with Mock LLM + LocalStack"
    echo "  ./docker-manage.sh start prod        # Production with AWS Bedrock"
    echo "  ./docker-manage.sh stop              # Stop containers (auto-backup)"
    echo "  ./docker-manage.sh stop --volumes    # Stop and remove data (auto-backup)"
    echo "  ./docker-manage.sh restart local     # Restart in local mode (auto-backup)"
    echo "  ./docker-manage.sh backup            # Create manual backup"
    echo "  ./docker-manage.sh restore           # Restore from latest backup (interactive)"
    echo "  ./docker-manage.sh logs backend      # View backend logs"
    echo "  ./docker-manage.sh migrate           # Run migrations"
    echo "  ./docker-manage.sh status            # Check container status"
    echo ""
    echo "Note: For macOS users with Vessel, use ./docker-manage-vessel.sh instead"
    echo ""
    exit 0
}

# Function to determine docker compose command
get_docker_compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    elif docker compose version &> /dev/null; then
        echo "docker compose"
    else
        echo "❌ Neither 'docker-compose' nor 'docker compose' is available"
        echo ""
        echo "Please install Docker Compose:"
        echo "  macOS: brew install docker-compose"
        echo "  Linux: sudo apt-get install docker-compose"
        echo ""
        exit 1
    fi
}

# Function to verify docker daemon access and provide actionable guidance
check_docker_access() {
    local docker_error

    if docker info > /dev/null 2>&1; then
        return 0
    fi

    docker_error=$(docker info 2>&1 || true)

    echo "❌ Cannot access Docker daemon"
    echo ""

    if echo "$docker_error" | grep -qiE "permission denied|/var/run/docker.sock"; then
        echo "   It looks like your user doesn't have permission to access /var/run/docker.sock."
        echo ""
        echo "   Linux fix (one-time):"
        echo "   1) sudo usermod -aG docker $USER"
        echo "   2) newgrp docker"
        echo "      (or log out and log back in)"
        echo "   3) docker info"
        echo "   4) ./docker-manage.sh start local"
    else
        echo "   Docker may not be running."
        echo ""
        echo "   Try:"
        echo "   1) sudo systemctl start docker"
        echo "   2) docker info"
        echo "   3) ./docker-manage.sh start local"
    fi

    echo ""
    echo "   Details: $docker_error"
    exit 1
}

# Function to check if a TCP port is already in use on localhost
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

# Function to resolve Redis host port conflicts
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
        echo "   Example: REDIS_HOST_PORT=6380 ./docker-manage.sh start $mode"
        exit 1
    fi

    if [[ "$mode" == "local" ]]; then
        local fallback_port
        for fallback_port in $(seq 6380 6399); do
            if ! is_port_in_use "$fallback_port"; then
                export REDIS_HOST_PORT="$fallback_port"
                echo "⚠️  Host port 6379 is busy; using Redis host port $REDIS_HOST_PORT for this run"
                echo "   To make this permanent, set REDIS_HOST_PORT=$REDIS_HOST_PORT in your local env file"
                return 0
            fi
        done

        echo "❌ Could not find a free fallback Redis host port in range 6380-6399"
        exit 1
    fi

    echo "❌ Redis host port 6379 is already in use"
    echo "   Set REDIS_HOST_PORT to a free port and retry"
    exit 1
}

# Function to load environment variables based on mode
load_env() {
    local mode=$1
    local local_env_file=".env.sample"

    if [[ ! -f "$local_env_file" && -f "env.sample" ]]; then
        local_env_file="env.sample"
    fi
    
    if [[ "$mode" == "local" ]]; then
        if [[ -f "$local_env_file" ]]; then
            echo "📋 Loading $local_env_file configuration..."
            export $(grep -v '^#' "$local_env_file" | xargs)
        else
            echo "⚠️  Warning: .env.sample/env.sample not found"
        fi
    elif [[ "$mode" == "prod" ]]; then
        if [[ -f ".env.prod" ]]; then
            echo "📋 Loading .env.prod configuration..."
            export $(grep -v '^#' .env.prod | xargs)
        else
            echo "⚠️  Warning: .env.prod not found"
        fi
    fi
    
    # Also load base .env if exists
    if [[ -f ".env" ]]; then
        export $(grep -v '^#' .env | xargs)
    fi
}

# Function to download HuggingFace models for RAG
download_models() {
    echo "📥 Checking HuggingFace models for RAG..."
    
    MODELS_DIR="./models"
    
    # Check if models directory exists and has content
    if [[ -d "$MODELS_DIR" && -n "$(ls -A $MODELS_DIR 2>/dev/null)" ]]; then
        echo "   ✅ Models directory exists and contains files"
        return 0
    fi
    
    echo "   📦 Models not found. Downloading required models..."
    echo "   This may take a few minutes on first run..."
    
    # Create models directory
    mkdir -p "$MODELS_DIR"
    
    # Check if Python3 and huggingface_hub are available
    if ! command -v python3 &> /dev/null; then
        echo "   ⚠️  Warning: python3 not found. Skipping model download."
        echo "   You can download models manually by running:"
        echo "   pip3 install huggingface_hub && python3 download_models.py"
        return 1
    fi
    
    # Install huggingface_hub if needed and download models
    if python3 -c "import huggingface_hub" 2>/dev/null; then
        python3 download_models.py
    else
        echo "   Installing huggingface_hub..."
        pip3 install huggingface_hub --quiet 2>/dev/null
        if [ $? -eq 0 ]; then
            python3 download_models.py
        else
            echo "   ⚠️  Warning: Could not install huggingface_hub"
            echo "   You can download models manually by running:"
            echo "   pip3 install huggingface_hub && python3 download_models.py"
            return 1
        fi
    fi
    
    echo ""
}

# Function to start containers
start_containers() {
    echo "🐳 $PROJECT_NAME Docker Service Management Script"
    echo "===================================================="
    
    MODE="local"
    ENV_FILE=".env.sample"
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.local.yml"
    
    if [[ "$1" == "local" || "$1" == "dev" || "$1" == "development" || -z "$1" ]]; then
        MODE="local"
        ENV_FILE=".env.sample"
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.local.yml"

        if [[ ! -f "$ENV_FILE" && -f "env.sample" ]]; then
            ENV_FILE="env.sample"
        fi

        export LOCAL_ENV_FILE="$ENV_FILE"
        echo "📋 Mode: Local Development"
        echo "   ✨ Features:"
        echo "      - Hot-reload enabled"
        echo "      - LocalStack for S3 emulation"
        echo "      - Mock LLM responses (no AWS costs)"
        echo "      - Debug mode enabled"
    elif [[ "$1" == "prod" || "$1" == "production" ]]; then
        MODE="prod"
        ENV_FILE=".env.prod"
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
        echo "📋 Mode: Production"
        echo "   🔒 Features:"
        echo "      - AWS Bedrock for LLM"
        echo "      - AWS S3 for storage"
        echo "      - AWS RDS for PostgreSQL (external)"
        echo "      - AWS ElastiCache for Redis (external)"
        echo "      - Frontend + Backend only (no local DB/Redis/LocalStack)"
        echo "      - No model downloads (uses AWS Bedrock embeddings)"
        echo "      - Optimized builds"
        echo "      - Production logging"
        echo "   🌐 Production URL: https://claimlen.com"
        echo "   📚 API Docs: https://claimlen.com/docs"
    else
        echo "❌ Invalid mode: $1"
        echo ""
        echo "Available modes:"
        echo "   local  - Local development with Mock LLM + LocalStack"
        echo "   prod   - Production with AWS Bedrock"
        echo ""
        show_help
    fi
    
    # Load environment variables
    load_env "$MODE"
    
    # Determine docker compose command
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    echo "📦 Using: $DOCKER_COMPOSE_CMD"

    # Check docker daemon access before any heavy work
    check_docker_access

    # Resolve Redis host port conflicts before compose up (only for local mode)
    if [[ "$MODE" == "local" ]]; then
        resolve_redis_port_conflict "$MODE"
    fi
    
    # Check if docker compose files exist
    echo ""
    echo "🔍 Checking Docker Compose files..."
    if [[ ! -f "docker-compose.yml" ]]; then
        echo "❌ Error: docker-compose.yml not found"
        exit 1
    fi
    
    if [[ "$MODE" == "local" && ! -f "docker-compose.local.yml" ]]; then
        echo "❌ Error: docker-compose.local.yml not found"
        echo "   Cannot start in local mode without docker-compose.local.yml"
        exit 1
    fi
    
    if [[ "$MODE" == "prod" && ! -f "docker-compose.prod.yml" ]]; then
        echo "❌ Error: docker-compose.prod.yml not found"
        echo "   Cannot start in production mode without docker-compose.prod.yml"
        exit 1
    fi
    
    # Check if env file exists
    echo "🔍 Checking environment file: $ENV_FILE..."
    if [[ ! -f "$ENV_FILE" ]]; then
        echo "⚠️  Warning: $ENV_FILE not found."
        if [[ "$MODE" == "local" ]]; then
            echo "   Expected one of: .env.sample or env.sample"
            echo "   Please review and update the values."
        fi
    fi
    
    # Download HuggingFace models for local RAG (if in local mode)
    # NOTE: Disabled for UI testing mode - uncomment if you need RAG functionality
    # if [[ "$MODE" == "local" ]]; then
    #     echo ""
    #     download_models
    # fi
    
    echo ""
    echo "🚀 Building and starting services..."
    echo "   This may take a few minutes on first run..."
    
    # For production mode, only start frontend and backend (AWS handles db/redis)
    if [[ "$MODE" == "prod" ]]; then
        echo "   📦 Production mode: Starting frontend and backend only"
        echo "   ☁️  Database and Redis are managed by AWS (RDS/ElastiCache)"
        DOCKER_BUILDKIT=0 $DOCKER_COMPOSE_CMD $COMPOSE_FILES up -d --build frontend backend
    else
        DOCKER_BUILDKIT=0 $DOCKER_COMPOSE_CMD $COMPOSE_FILES up -d --build
    fi
    
    echo ""
    echo "⏳ Waiting for services to be healthy..."
    sleep 10
    
    # Only check local db/redis health for local mode
    if [[ "$MODE" == "local" ]]; then
        # Wait for postgres to be ready
        echo "🔍 Checking PostgreSQL health..."
        max_retries=30
        retry_count=0
        while [ $retry_count -lt $max_retries ]; do
            if $DOCKER_COMPOSE_CMD $COMPOSE_FILES exec -T db pg_isready -U ${DB_USER:-postgres} &> /dev/null; then
                echo "✅ PostgreSQL is ready"
                break
            fi
            retry_count=$((retry_count + 1))
            echo "   Waiting for PostgreSQL... ($retry_count/$max_retries)"
            sleep 2
        done
        
        if [ $retry_count -eq $max_retries ]; then
            echo "⚠️  Warning: PostgreSQL health check timed out"
        fi
        
        # Wait for Redis to be ready
        echo ""
        echo "🔍 Checking Redis health..."
        retry_count=0
        while [ $retry_count -lt $max_retries ]; do
            if $DOCKER_COMPOSE_CMD $COMPOSE_FILES exec -T redis redis-cli ping &> /dev/null; then
                echo "✅ Redis is ready"
                break
            fi
            retry_count=$((retry_count + 1))
            echo "   Waiting for Redis... ($retry_count/$max_retries)"
            sleep 2
        done
        
        if [ $retry_count -eq $max_retries ]; then
            echo "⚠️  Warning: Redis health check timed out"
        fi
        
        # LocalStack health check - DISABLED for UI testing mode
        # Uncomment if you enable localstack in docker-compose.local.yml
        # echo ""
        # echo "🔍 Checking LocalStack health..."
        # retry_count=0
        # max_localstack_retries=15  # Shorter timeout for LocalStack
        # while [ $retry_count -lt $max_localstack_retries ]; do
        #     # Check using docker's health status which is more reliable
        #     HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' ${CONTAINER_PREFIX}-localstack 2>/dev/null || echo "unknown")
        #     if [[ "$HEALTH_STATUS" == "healthy" ]]; then
        #         echo "✅ LocalStack is ready"
        #         break
        #     fi
        #     retry_count=$((retry_count + 1))
        #     echo "   Waiting for LocalStack... ($retry_count/$max_localstack_retries) [status: $HEALTH_STATUS]"
        #     sleep 2
        # done
        #
        # if [ $retry_count -eq $max_localstack_retries ]; then
        #     echo "⚠️  Warning: LocalStack health check timed out (continuing anyway)"
        # fi
        echo ""
        echo "ℹ️  LocalStack disabled (UI testing mode)"
    else
        # Production mode - just check backend health
        echo "🔍 Checking Backend health..."
        retry_count=0
        max_retries=30
        while [ $retry_count -lt $max_retries ]; do
            if curl -sf http://localhost:8000/health &> /dev/null; then
                echo "✅ Backend is ready"
                break
            fi
            retry_count=$((retry_count + 1))
            echo "   Waiting for Backend... ($retry_count/$max_retries)"
            sleep 2
        done
        
        if [ $retry_count -eq $max_retries ]; then
            echo "⚠️  Warning: Backend health check timed out"
        fi
    fi
    
    # Run database migrations
    echo ""
    echo "📊 Running database migrations..."
    if $DOCKER_COMPOSE_CMD $COMPOSE_FILES exec -T backend alembic upgrade head 2>/dev/null; then
        echo "✅ Database migrations completed"
    else
        echo "⚠️  Note: Could not run migrations (backend may still be starting)"
        echo "   You can run migrations manually later with:"
        echo "   ./docker-manage.sh migrate"
    fi
    
    # Check status
    echo ""
    echo "📊 Service Status:"
    $DOCKER_COMPOSE_CMD $COMPOSE_FILES ps
    
    echo ""
    echo "✅ Services started successfully in $MODE mode"
    
    echo ""
    echo "🌐 Access Points:"
    if [[ "$MODE" == "local" ]]; then
        echo "   - Frontend (Dev):      http://localhost:3000"
        echo "   - Backend API:         http://localhost:8000"
        echo "   - Swagger Docs:        http://localhost:8000/docs"
        echo "   - ReDoc:               http://localhost:8000/redoc"
        echo "   - OpenAPI JSON:        http://localhost:8000/openapi.json"
        echo "   - Health Check:        http://localhost:8000/health"
        echo "   - LocalStack S3:       http://localhost:4566"
        echo ""
        echo "🤖 LLM Configuration:"
        echo "   - Mode: Mock LLM (no AWS costs)"
        echo "   - Responses: Simulated for development"
    else
        echo "   - Frontend:            https://claimlen.com"
        echo "   - Backend API:         https://claimlen.com/api/v1"
        echo "   - Swagger Docs:        https://claimlen.com/docs"
        echo "   - ReDoc:               https://claimlen.com/redoc"
        echo "   - OpenAPI JSON:        https://claimlen.com/openapi.json"
        echo "   - Health Check:        https://claimlen.com/health"
        echo ""
        echo "🤖 LLM Configuration:"
        echo "   - Mode: AWS Bedrock"
        echo "   - Model: ${BEDROCK_MODEL_ID:-anthropic.claude-3-haiku-20240307-v1:0}"
        echo ""
        echo "☁️  AWS Managed Services (external):"
        echo "   - PostgreSQL:          AWS RDS (configured in .env.prod)"
        echo "   - Redis:               AWS ElastiCache (configured in .env.prod)"
        echo "   - S3 Storage:          AWS S3 (configured in .env.prod)"
    fi
    if [[ "$MODE" == "local" ]]; then
        echo "   - PostgreSQL:          localhost:5432"
        echo "   - Redis:               localhost:${REDIS_HOST_PORT:-6379}"
    fi
    echo ""
    echo "📋 Useful Commands:"
    echo "   - View all logs: ./docker-manage.sh logs"
    echo "   - View backend logs: ./docker-manage.sh logs backend"
    echo "   - View frontend logs: ./docker-manage.sh logs frontend"
    echo "   - Check status: ./docker-manage.sh status"
    echo "   - Run migrations: ./docker-manage.sh migrate"
    echo "   - Stop services: ./docker-manage.sh stop"
}

# Function to stop containers
stop_containers() {
    echo "🛑 $PROJECT_NAME Docker Service Stop Script"
    echo "=============================================="
    
    # Determine docker compose command
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    
    # Auto-backup before stopping
    auto_backup_before_stop
    
    if [[ "$1" == "--volumes" ]]; then
        echo "📋 Mode: Stop and remove volumes (clean shutdown)"
        echo ""
        echo "🛑 Stopping services and removing volumes..."
        $DOCKER_COMPOSE_CMD down -v --remove-orphans
        echo "✅ Services stopped and volumes removed"
    else
        echo "📋 Mode: Stop services (preserve data)"
        echo ""
        echo "🛑 Stopping services..."
        $DOCKER_COMPOSE_CMD down --remove-orphans
        echo "✅ Services stopped (volumes preserved)"
    fi
    
    echo ""
    echo "📋 Useful Commands:"
    echo "   - Start local: ./docker-manage.sh start local"
    echo "   - Start prod: ./docker-manage.sh start prod"
    echo "   - Restart: ./docker-manage.sh restart"
    echo "   - Restore backup: ./docker-manage.sh restore [backup_file]"
}

# Function to restart containers
restart_containers() {
    echo "🔄 $PROJECT_NAME Docker Service Restart Script"
    echo "================================================="
    
    MODE="local"
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.local.yml"
    
    if [[ "$1" == "local" || "$1" == "dev" || "$1" == "development" || -z "$1" ]]; then
        MODE="local"
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.local.yml"
        echo "📋 Mode: Local Development"
        echo "   ✨ Features: Mock LLM, LocalStack, hot-reload"
    elif [[ "$1" == "prod" || "$1" == "production" ]]; then
        MODE="prod"
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
        echo "📋 Mode: Production"
        echo "   🔒 Features: AWS Bedrock, production settings"
        echo "   🌐 Production URL: https://claimlen.com"
        echo "   📚 API Docs: https://claimlen.com/docs"
    else
        echo "❌ Invalid mode: $1"
        echo ""
        show_help
    fi
    
    # Determine docker compose command
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    echo "📦 Using: $DOCKER_COMPOSE_CMD"
    
    echo ""
    # Auto-backup before restarting
    auto_backup_before_stop
    
    echo "🛑 Stopping existing services..."
    $DOCKER_COMPOSE_CMD $COMPOSE_FILES down --remove-orphans 2>/dev/null || true
    
    # Now start with the same parameters
    start_containers "$1"
}

# Function to show status
show_status() {
    echo "🐳 $PROJECT_NAME Docker Status"
    echo "================================="
    
    # Determine docker compose command
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    
    echo ""
    echo "📊 Container Status:"
    $DOCKER_COMPOSE_CMD ps
    
    echo ""
    echo "📈 Container Resource Usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" $(docker ps --format '{{.Names}}' | grep $CONTAINER_PREFIX) 2>/dev/null || echo "No $PROJECT_NAME containers running"
    
    echo ""
    echo "🔧 Current Configuration:"
    if docker ps --format '{{.Names}}' | grep -q "${CONTAINER_PREFIX}-localstack"; then
        echo "   Mode: Local Development (LocalStack + Mock LLM)"
    else
        echo "   Mode: Production (AWS Bedrock)"
    fi
}

# Function to view logs
view_logs() {
    # Determine docker compose command
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    
    SERVICE=$1
    
    if [[ -z "$SERVICE" ]]; then
        echo "📋 Viewing all logs (Ctrl+C to exit)..."
        echo ""
        $DOCKER_COMPOSE_CMD logs -f
    else
        echo "📋 Viewing logs for: $SERVICE (Ctrl+C to exit)..."
        echo ""
        docker logs -f "${CONTAINER_PREFIX}-${SERVICE}" 2>/dev/null || $DOCKER_COMPOSE_CMD logs -f "$SERVICE"
    fi
}

# Function to execute bash in container
exec_container() {
    SERVICE=${1:-backend}
    CONTAINER_NAME="${CONTAINER_PREFIX}-${SERVICE}"
    
    echo "💻 Opening shell in: $SERVICE"
    echo ""
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        if [[ "$SERVICE" == "db" ]]; then
            # Get database name from environment or use default
            DB_NAME=${DB_NAME:-claimlens}
            DB_USER=${DB_USER:-postgres}
            echo "Connecting to database: $DB_NAME as user: $DB_USER"
            docker exec -it "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME"
        elif [[ "$SERVICE" == "redis" ]]; then
            docker exec -it "$CONTAINER_NAME" redis-cli
        else
            docker exec -it "$CONTAINER_NAME" bash 2>/dev/null || docker exec -it "$CONTAINER_NAME" sh
        fi
    else
        echo "❌ Container $CONTAINER_NAME is not running"
        echo ""
        echo "Start the application first: ./docker-manage.sh start"
        exit 1
    fi
}

# Function to run migrations
run_migrations() {
    echo "📊 Running database migrations..."
    echo ""
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-backend$"; then
        docker exec -it ${CONTAINER_PREFIX}-backend alembic upgrade head
        echo ""
        echo "✅ Migrations completed"
    else
        echo "❌ Backend container is not running"
        echo ""
        echo "Start the application first: ./docker-manage.sh start"
        exit 1
    fi
}

# Function to seed database
seed_database() {
    echo "🌱 Seeding database with sample data..."
    echo ""
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-backend$"; then
        docker exec -it ${CONTAINER_PREFIX}-backend python -m scripts.seed_data 2>/dev/null || \
        docker exec -it ${CONTAINER_PREFIX}-backend python scripts/seed_data.py
        echo ""
        echo "✅ Database seeded successfully"
    else
        echo "❌ Backend container is not running"
        echo ""
        echo "Start the application first: ./docker-manage.sh start"
        exit 1
    fi
}

# Function to backup database
backup_database() {
    # Create backups directory if it doesn't exist
    BACKUP_DIR="./backups"
    mkdir -p "$BACKUP_DIR"
    
    # Set compression level
    COMPRESSION_LEVEL=${BACKUP_COMPRESSION_LEVEL:-9}
    
    echo "💾 Backing up database..."
    echo ""
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-db$"; then
        # Check if database has data before creating backup
        echo "🔍 Checking if database has data..."
        # Get database name from environment or use default
        DB_NAME=${DB_NAME:-claimlens}
        DB_USER=${DB_USER:-postgres}
        
        echo "Using database: $DB_NAME with user: $DB_USER"
        
        HAS_DATA=$(docker exec ${CONTAINER_PREFIX}-db psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM (SELECT 1 FROM information_schema.tables t WHERE t.table_schema = 'public' LIMIT 1) AS has_data;" 2>/dev/null || echo "0")
        
        # Trim whitespace from result
        HAS_DATA=$(echo "$HAS_DATA" | tr -d '[:space:]')
        
        if [ "$HAS_DATA" -eq "0" ] 2>/dev/null; then
            echo "⚠️  Database appears to be empty - skipping backup"
            return 0
        fi
        
        echo "✅ Database has data, proceeding with backup..."
        
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_FILE="${BACKUP_DIR}/${CONTAINER_PREFIX}_backup_${TIMESTAMP}.sql"
        
        echo "📊 Creating backup..."
        
        # Standard backup with compression
        docker exec ${CONTAINER_PREFIX}-db pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc -Z "$COMPRESSION_LEVEL" -f "/tmp/backup.dump"
        
        # Copy from container to host
        docker cp ${CONTAINER_PREFIX}-db:/tmp/backup.dump "$BACKUP_FILE"
        
        if [ -f "$BACKUP_FILE" ]; then
            FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
            echo "✅ Database backed up successfully!"
            echo "   📁 Location: $BACKUP_FILE"
            echo "   📊 Size: $FILE_SIZE"
        else
            echo "❌ Backup failed - file not created"
            return 1
        fi
        
        # Keep only last 10 backups to save disk space
        echo ""
        echo "🧹 Managing backup retention (keeping last 10 backups)..."
        
        cd "$BACKUP_DIR"
        ls -t ${CONTAINER_PREFIX}_backup_*.sql 2>/dev/null | tail -n +11 | xargs -r rm -- 2>/dev/null || true
        
        # Count remaining backups
        BACKUP_COUNT=$(ls -1 ${CONTAINER_PREFIX}_backup_*.sql 2>/dev/null | wc -l)
        echo "   📚 Total backups: $BACKUP_COUNT"
        cd - > /dev/null
    else
        echo "⚠️  PostgreSQL container is not running - skipping backup"
        return 1
    fi
}

# Function to auto-backup before stopping (if containers are running)
auto_backup_before_stop() {
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-db$"; then
        echo "🔒 Auto-backup before stopping containers..."
        echo "   (Protecting your data)"
        echo ""
        backup_database
        echo ""
    fi
}

# Function to restore database from backup
restore_database() {
    BACKUP_DIR="./backups"
    
    echo "🔄 Restoring database from backup..."
    echo ""
    
    # Check if backup directory exists
    if [[ ! -d "$BACKUP_DIR" ]]; then
        echo "❌ Backup directory not found: $BACKUP_DIR"
        exit 1
    fi
    
    # Check for auto mode
    AUTO_MODE=false
    if [[ "$1" == "--auto" ]]; then
        AUTO_MODE=true
        # Try to find the latest backup
        BACKUP_FILE=$(ls -t "$BACKUP_DIR"/${CONTAINER_PREFIX}_backup_*.sql 2>/dev/null | head -n 1)
        
        if [[ -z "$BACKUP_FILE" ]]; then
            echo "❌ No backup files found in $BACKUP_DIR"
            exit 1
        fi
        
        echo "Using latest backup in auto mode: $BACKUP_FILE"
    # If backup file is provided as argument
    elif [[ -n "$1" && "$1" != "--auto" ]]; then
        BACKUP_FILE="$1"
        if [[ ! -f "$BACKUP_FILE" ]]; then
            echo "❌ Backup file not found: $BACKUP_FILE"
            exit 1
        fi
    else
        # List available backups
        echo "📁 Available backups:"
        echo ""
        ls -lht "$BACKUP_DIR"/${CONTAINER_PREFIX}_backup_*.sql 2>/dev/null | awk '{print NR". "$9" ("$5")"}'
        
        if ! ls "$BACKUP_DIR"/${CONTAINER_PREFIX}_backup_*.sql >/dev/null 2>&1; then
            echo "❌ No backup files found in $BACKUP_DIR"
            exit 1
        fi
        
        # Automatically use the latest backup
        BACKUP_FILE=$(ls -t "$BACKUP_DIR"/${CONTAINER_PREFIX}_backup_*.sql 2>/dev/null | head -n 1)
        echo ""
        echo "Using latest backup: $BACKUP_FILE"
    fi
    
    echo ""
    echo "⚠️  WARNING: This will replace ALL current database data!"
    echo "   Backup file: $BACKUP_FILE"
    
    if [[ "$AUTO_MODE" == "true" ]]; then
        echo "   Auto mode: proceeding with restore automatically..."
        echo
    else
        read -p "Are you sure you want to restore? (yes/no): " -r
        echo
        
        if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
            echo "❌ Restore cancelled"
            exit 0
        fi
    fi
    
    # Check if postgres container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-db$"; then
        echo "❌ PostgreSQL container is not running"
        echo "   Start the application first: ./docker-manage.sh start"
        exit 1
    fi
    
    echo "🔄 Restoring database..."
    
    # Get database name from environment or use default
    DB_NAME=${DB_NAME:-claimlens}
    DB_USER=${DB_USER:-postgres}
    
    echo "Using database: $DB_NAME with user: $DB_USER"
    
    # Copy backup to container
    docker cp "$BACKUP_FILE" ${CONTAINER_PREFIX}-db:/tmp/restore.dump
    
    # Drop existing connections and recreate database
    docker exec ${CONTAINER_PREFIX}-db psql -U "$DB_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" 2>/dev/null || true
    docker exec ${CONTAINER_PREFIX}-db psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null
    docker exec ${CONTAINER_PREFIX}-db psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null
    
    # Restore backup
    docker exec ${CONTAINER_PREFIX}-db pg_restore -U "$DB_USER" -d "$DB_NAME" /tmp/restore.dump 2>/dev/null || \
        docker exec -i ${CONTAINER_PREFIX}-db psql -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE"
    
    RESTORE_RESULT=$?
    if [[ $RESTORE_RESULT -eq 0 ]]; then
        echo ""
        echo "✅ Database restored successfully from:"
        echo "   📁 $BACKUP_FILE"
        echo ""
        echo "📋 Next steps:"
        if [[ "$AUTO_MODE" == "true" ]]; then
            echo "   🔄 Auto-restarting services..."
            
            # Restart backend
            docker restart ${CONTAINER_PREFIX}-backend
            echo "   ✅ Backend service restarted"
            
            # Wait for services to be ready
            echo "   ⏳ Waiting for services to be ready..."
            sleep 10
            echo "   ✅ Services should now be ready"
        else
            echo "   - Restart backend: docker restart ${CONTAINER_PREFIX}-backend"
            echo "   - Or restart all: ./docker-manage.sh restart"
        fi
    else
        echo "❌ Restore failed"
        exit 1
    fi
}

# Function to clean everything
clean_all() {
    echo "🧹 $PROJECT_NAME Docker Clean Script"
    echo "======================================="
    echo ""
    echo "⚠️  WARNING: This will stop all containers and remove all data!"
    read -p "Are you sure? (yes/no): " -r
    echo
    
    if [[ $REPLY =~ ^[Yy]es$ ]]; then
        # Determine docker compose command
        DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
        
        # Auto-backup before cleaning
        echo ""
        auto_backup_before_stop
        
        echo "🧹 Cleaning up..."
        $DOCKER_COMPOSE_CMD down -v --remove-orphans
        echo "✅ Cleanup completed"
    else
        echo "❌ Cleanup cancelled"
    fi
}

# Function for scheduled backups (to be used with cron jobs)
scheduled_backup() {
    # Create logs directory if it doesn't exist
    LOGS_DIR="./logs"
    mkdir -p "$LOGS_DIR"
    LOG_FILE="$LOGS_DIR/backup.log"
    
    # Log start of backup process
    echo "$(date): Starting scheduled backup..." >> "$LOG_FILE"
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        echo "$(date): Docker is not running, skipping backup" >> "$LOG_FILE"
        exit 0
    fi
    
    # Check if the postgres container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-db$"; then
        echo "$(date): PostgreSQL container is not running, skipping backup" >> "$LOG_FILE"
        exit 0
    fi
    
    # Redirect output to log file
    {
        # Run the backup
        echo "$(date): Running database backup..."
        backup_database
        
        # Log completion
        echo "$(date): Scheduled backup completed"
    } >> "$LOG_FILE" 2>&1
}

# Function to fix postgres permissions
fix_postgres() {
    # Get database name from environment or use default
    DB_NAME=${DB_NAME:-claimlens}
    DB_USER=${DB_USER:-postgres}
    
    echo "🔧 Fixing postgres user for database: $DB_NAME"
    echo ""
    
    # Check if postgres container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-db$"; then
        echo "❌ PostgreSQL container is not running"
        echo "   Start the application first: ./docker-manage.sh start"
        exit 1
    fi
    
    # Enable pgvector extension
    echo "🔧 Enabling pgvector extension..."
    docker exec ${CONTAINER_PREFIX}-db psql -U "$DB_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true
    
    echo ""
    echo "✅ Postgres setup completed"
    echo ""
    echo "🔍 You can now connect to the database using:"
    echo "   - Username: $DB_USER"
    echo "   - Password: (from your .env file)"
    echo "   - Database: $DB_NAME"
    echo "   - Host: localhost"
    echo "   - Port: 5432"
}

# ============================================
# AWS/LocalStack Management Functions
# ============================================

# Function to setup AWS credentials
aws_setup() {
    echo "🔧 AWS Configuration Setup"
    echo "==========================="
    echo ""
    
    echo "📋 Environment Configuration Files:"
    echo ""
    echo "   .env.sample (Local Development):"
    if [[ -f ".env.sample" ]]; then
        echo "      ✅ Found"
        echo "      - USE_LOCALSTACK=true"
        echo "      - USE_MOCK_LLM=true"
        echo "      - No AWS costs during development"
    else
        echo "      ❌ Not found"
    fi
    echo ""
    echo "   .env.prod (Production):"
    if [[ -f ".env.prod" ]]; then
        echo "      ✅ Found"
        source .env.prod 2>/dev/null || true
        echo "      - AWS_REGION: ${AWS_REGION:-not set}"
        echo "      - BEDROCK_MODEL_ID: ${BEDROCK_MODEL_ID:-not set}"
        echo "      - BEDROCK_ENABLED: ${BEDROCK_ENABLED:-false}"
    else
        echo "      ❌ Not found"
    fi
    echo ""
    echo "📋 Available LLM Models (AWS Bedrock):"
    echo "   - anthropic.claude-3-haiku-20240307-v1:0 (fast, cost-effective)"
    echo "   - anthropic.claude-3-sonnet-20240229-v1:0 (balanced)"
    echo "   - anthropic.claude-3-opus-20240229-v1:0 (most capable)"
    echo ""
    echo "📋 Commands:"
    echo "   Local development: ./docker-manage.sh start local"
    echo "   Production: ./docker-manage.sh start prod"
}

# Function to create S3 bucket in LocalStack
s3_create_bucket() {
    echo "📦 Creating S3 bucket in LocalStack..."
    echo ""
    
    BUCKET_NAME=${S3_BUCKET_NAME:-claimlens-prod-documents-ap-south-1}
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-localstack$"; then
        echo "❌ LocalStack is not running"
        echo "   Start with: ./docker-manage.sh start local"
        exit 1
    fi
    
    # Create bucket using AWS CLI in LocalStack
    docker exec ${CONTAINER_PREFIX}-localstack awslocal s3 mb s3://${BUCKET_NAME} 2>/dev/null || true
    
    echo "✅ S3 bucket created: $BUCKET_NAME"
    echo ""
    echo "📋 You can now upload files to:"
    echo "   s3://${BUCKET_NAME}/"
}

# Function to list S3 files
s3_list() {
    echo "📦 Listing S3 bucket contents..."
    echo ""
    
    BUCKET_NAME=${S3_BUCKET_NAME:-claimlens-prod-documents-ap-south-1}
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-localstack$"; then
        echo "❌ LocalStack is not running"
        echo "   Start with: ./docker-manage.sh start local"
        exit 1
    fi
    
    docker exec ${CONTAINER_PREFIX}-localstack awslocal s3 ls s3://${BUCKET_NAME}/ --recursive 2>/dev/null || echo "Bucket is empty or doesn't exist"
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
    # AWS commands
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
        echo ""
        show_help
        ;;
esac
