#!/bin/bash

# ClaimLens Insurance Docker Management Script - Vessel Version
# For macOS users with Apple Vessel compatibility
# Usage: ./docker-manage-vessel.sh [command] [options]

set -e

# Project configuration
PROJECT_NAME="ClaimLens"
CONTAINER_PREFIX="claimlens"

# Function to show help
show_help() {
    echo "🐳 $PROJECT_NAME Docker Management Script (Vessel)"
    echo "===================================================="
    echo ""
    echo "This script is for macOS users with Apple Vessel installed."
    echo "For standard Docker usage, use ./docker-manage.sh instead."
    echo ""
    echo "Usage: ./docker-manage-vessel.sh [COMMAND] [OPTIONS]"
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
    echo "  restore [backup_file]   - Restore database from backup"
    echo "  clean                   - Stop containers and remove volumes (auto-backup)"
    echo "  help                    - Show this help message"
    echo ""
    echo "Modes:"
    echo "  local      - Local development with LocalStack & Mock LLM"
    echo "  prod       - Production mode with AWS Bedrock"
    echo ""
    echo "Examples:"
    echo "  ./docker-manage-vessel.sh start local"
    echo "  ./docker-manage-vessel.sh start prod"
    echo "  ./docker-manage-vessel.sh stop"
    echo "  ./docker-manage-vessel.sh logs backend"
    echo ""
    exit 0
}

# Function to setup and check vessel compatibility (for macOS)
setup_vessel_compat() {
    if [[ "$OSTYPE" != "darwin"* ]]; then
        echo "⚠️  This script is for macOS with Vessel."
        echo "   Use ./docker-manage.sh for other systems."
        exit 1
    fi
    
    if ! command -v vessel &> /dev/null; then
        echo "❌ Vessel is not installed."
        echo ""
        echo "This script requires Apple Vessel for macOS."
        echo "Use ./docker-manage.sh instead for standard Docker."
        exit 1
    fi
    
    echo "📋 Setting up vessel compatibility mode..."
    
    # Check if vessel compat is enabled
    if ! vessel compat status &> /dev/null; then
        echo "❌ Vessel compat mode not enabled."
        echo ""
        echo "Please run this command first:"
        echo "  vessel compat"
        echo ""
        exit 1
    fi
    
    # Export the environment variables in this script's process
    echo "🔧 Loading vessel environment variables..."
    eval "$(vessel compat env)"
    
    echo "✅ Vessel environment loaded successfully"
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
        echo ""
        exit 1
    fi
}

# Function to load environment variables based on mode
load_env() {
    local mode=$1
    
    if [[ "$mode" == "local" ]]; then
        if [[ -f ".env.local" ]]; then
            echo "📋 Loading .env.local configuration..."
            export $(grep -v '^#' .env.local | xargs)
        fi
    elif [[ "$mode" == "prod" ]]; then
        if [[ -f ".env.prod" ]]; then
            echo "📋 Loading .env.prod configuration..."
            export $(grep -v '^#' .env.prod | xargs)
        fi
    fi
    
    if [[ -f ".env" ]]; then
        export $(grep -v '^#' .env | xargs)
    fi
}

# Function to start containers
start_containers() {
    echo "🐳 $PROJECT_NAME Docker Service (Vessel Mode)"
    echo "==============================================="
    
    # Setup vessel first
    setup_vessel_compat
    
    MODE="local"
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.local.yml"
    
    if [[ "$1" == "local" || "$1" == "dev" || -z "$1" ]]; then
        MODE="local"
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.local.yml"
        echo "📋 Mode: Local Development"
        echo "   ✨ Features: Mock LLM, LocalStack, hot-reload"
    elif [[ "$1" == "prod" || "$1" == "production" ]]; then
        MODE="prod"
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
        echo "📋 Mode: Production"
        echo "   🔒 Features: AWS Bedrock, production settings"
    else
        echo "❌ Invalid mode: $1"
        show_help
    fi
    
    load_env "$MODE"
    
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    echo "📦 Using: $DOCKER_COMPOSE_CMD"
    
    echo ""
    echo "🚀 Building and starting services..."
    DOCKER_BUILDKIT=0 $DOCKER_COMPOSE_CMD $COMPOSE_FILES up -d --build
    
    echo ""
    echo "⏳ Waiting for services to be healthy..."
    sleep 10
    
    # Health checks
    max_retries=30
    retry_count=0
    
    echo "🔍 Checking PostgreSQL health..."
    while [ $retry_count -lt $max_retries ]; do
        if $DOCKER_COMPOSE_CMD $COMPOSE_FILES exec -T db pg_isready -U ${DB_USER:-postgres} &> /dev/null; then
            echo "✅ PostgreSQL is ready"
            break
        fi
        retry_count=$((retry_count + 1))
        echo "   Waiting for PostgreSQL... ($retry_count/$max_retries)"
        sleep 2
    done
    
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
    
    if [[ "$MODE" == "local" ]]; then
        echo ""
        echo "🔍 Checking LocalStack health..."
        retry_count=0
        max_localstack_retries=15  # Shorter timeout for LocalStack
        while [ $retry_count -lt $max_localstack_retries ]; do
            # Check using docker's health status which is more reliable
            HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' ${CONTAINER_PREFIX}-localstack 2>/dev/null || echo "unknown")
            if [[ "$HEALTH_STATUS" == "healthy" ]]; then
                echo "✅ LocalStack is ready"
                break
            fi
            retry_count=$((retry_count + 1))
            echo "   Waiting for LocalStack... ($retry_count/$max_localstack_retries) [status: $HEALTH_STATUS]"
            sleep 2
        done
        
        if [ $retry_count -eq $max_localstack_retries ]; then
            echo "⚠️  Warning: LocalStack health check timed out (continuing anyway)"
        fi
    fi
    
    echo ""
    echo "📊 Running database migrations..."
    $DOCKER_COMPOSE_CMD $COMPOSE_FILES exec -T backend alembic upgrade head 2>/dev/null || echo "⚠️  Migrations skipped"
    
    echo ""
    echo "📊 Service Status:"
    $DOCKER_COMPOSE_CMD $COMPOSE_FILES ps
    
    echo ""
    echo "✅ Services started successfully in $MODE mode (Vessel)"
    echo ""
    echo "🌐 Access Points:"
    if [[ "$MODE" == "local" ]]; then
        echo "   - Frontend:            http://localhost:3000"
        echo "   - Backend API:         http://localhost:8000"
        echo "   - Swagger Docs:        http://localhost:8000/docs"
        echo "   - ReDoc:               http://localhost:8000/redoc"
        echo "   - OpenAPI JSON:        http://localhost:8000/openapi.json"
        echo "   - Health Check:        http://localhost:8000/health"
        echo "   - LocalStack S3:       http://localhost:4566"
    else
        echo "   - Frontend:            http://localhost"
        echo "   - Backend API:         http://localhost:8000"
        echo "   - Swagger Docs:        http://localhost:8000/docs"
        echo "   - ReDoc:               http://localhost:8000/redoc"
        echo "   - OpenAPI JSON:        http://localhost:8000/openapi.json"
        echo "   - Health Check:        http://localhost:8000/health"
    fi
}

# Function to stop containers
stop_containers() {
    echo "🛑 $PROJECT_NAME Docker Stop (Vessel Mode)"
    echo "============================================"
    
    setup_vessel_compat
    
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    
    # Auto-backup
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-db$"; then
        echo "🔒 Auto-backup before stopping..."
        backup_database
    fi
    
    if [[ "$1" == "--volumes" ]]; then
        echo "🛑 Stopping and removing volumes..."
        $DOCKER_COMPOSE_CMD down -v --remove-orphans
    else
        echo "🛑 Stopping services..."
        $DOCKER_COMPOSE_CMD down --remove-orphans
    fi
    
    echo "✅ Services stopped"
}

# Function to restart containers
restart_containers() {
    echo "🔄 $PROJECT_NAME Docker Restart (Vessel Mode)"
    echo "==============================================="
    
    setup_vessel_compat
    
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    
    MODE="local"
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.local.yml"
    
    if [[ "$1" == "prod" || "$1" == "production" ]]; then
        MODE="prod"
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
    fi
    
    # Auto-backup
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-db$"; then
        echo "🔒 Auto-backup before restart..."
        backup_database
    fi
    
    echo "🛑 Stopping existing services..."
    $DOCKER_COMPOSE_CMD $COMPOSE_FILES down --remove-orphans 2>/dev/null || true
    
    start_containers "$1"
}

# Function to show status
show_status() {
    echo "🐳 $PROJECT_NAME Docker Status (Vessel Mode)"
    echo "=============================================="
    
    setup_vessel_compat
    
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    
    echo ""
    echo "📊 Container Status:"
    $DOCKER_COMPOSE_CMD ps
    
    echo ""
    echo "📈 Container Resource Usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" $(docker ps --format '{{.Names}}' | grep $CONTAINER_PREFIX) 2>/dev/null || echo "No containers running"
}

# Function to view logs
view_logs() {
    setup_vessel_compat
    
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    
    SERVICE=$1
    
    if [[ -z "$SERVICE" ]]; then
        echo "📋 Viewing all logs (Ctrl+C to exit)..."
        $DOCKER_COMPOSE_CMD logs -f
    else
        echo "📋 Viewing logs for: $SERVICE (Ctrl+C to exit)..."
        docker logs -f "${CONTAINER_PREFIX}-${SERVICE}" 2>/dev/null || $DOCKER_COMPOSE_CMD logs -f "$SERVICE"
    fi
}

# Function to execute bash in container
exec_container() {
    setup_vessel_compat
    
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
        exit 1
    fi
}

# Function to run migrations
run_migrations() {
    setup_vessel_compat
    
    echo "📊 Running database migrations..."
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-backend$"; then
        docker exec -it ${CONTAINER_PREFIX}-backend alembic upgrade head
        echo "✅ Migrations completed"
    else
        echo "❌ Backend container is not running"
        exit 1
    fi
}

# Function to seed database
seed_database() {
    setup_vessel_compat
    
    echo "🌱 Seeding database..."
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-backend$"; then
        docker exec -it ${CONTAINER_PREFIX}-backend python -m scripts.seed_data 2>/dev/null || \
        docker exec -it ${CONTAINER_PREFIX}-backend python scripts/seed_data.py
        echo "✅ Database seeded"
    else
        echo "❌ Backend container is not running"
        exit 1
    fi
}

# Function to backup database
backup_database() {
    setup_vessel_compat
    
    BACKUP_DIR="./backups"
    mkdir -p "$BACKUP_DIR"
    
    echo "💾 Backing up database..."
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-db$"; then
        DB_NAME=${DB_NAME:-claimlens}
        DB_USER=${DB_USER:-postgres}
        
        HAS_DATA=$(docker exec ${CONTAINER_PREFIX}-db psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM (SELECT 1 FROM information_schema.tables t WHERE t.table_schema = 'public' LIMIT 1) AS has_data;" 2>/dev/null || echo "0")
        HAS_DATA=$(echo "$HAS_DATA" | tr -d '[:space:]')
        
        if [ "$HAS_DATA" -eq "0" ] 2>/dev/null; then
            echo "⚠️  Database empty - skipping backup"
            return 0
        fi
        
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_FILE="${BACKUP_DIR}/${CONTAINER_PREFIX}_backup_${TIMESTAMP}.sql"
        
        docker exec ${CONTAINER_PREFIX}-db pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc -Z 9 -f "/tmp/backup.dump"
        docker cp ${CONTAINER_PREFIX}-db:/tmp/backup.dump "$BACKUP_FILE"
        
        if [ -f "$BACKUP_FILE" ]; then
            FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
            echo "✅ Backup saved: $BACKUP_FILE ($FILE_SIZE)"
        fi
        
        # Keep only last 10 backups
        cd "$BACKUP_DIR"
        ls -t ${CONTAINER_PREFIX}_backup_*.sql 2>/dev/null | tail -n +11 | xargs -r rm -- 2>/dev/null || true
        cd - > /dev/null
    else
        echo "⚠️  PostgreSQL not running"
    fi
}

# Function to restore database
restore_database() {
    setup_vessel_compat
    
    BACKUP_DIR="./backups"
    
    echo "🔄 Restoring database..."
    
    if [[ "$1" == "--auto" ]]; then
        BACKUP_FILE=$(ls -t "$BACKUP_DIR"/${CONTAINER_PREFIX}_backup_*.sql 2>/dev/null | head -n 1)
    elif [[ -n "$1" ]]; then
        BACKUP_FILE="$1"
    else
        BACKUP_FILE=$(ls -t "$BACKUP_DIR"/${CONTAINER_PREFIX}_backup_*.sql 2>/dev/null | head -n 1)
    fi
    
    if [[ -z "$BACKUP_FILE" || ! -f "$BACKUP_FILE" ]]; then
        echo "❌ No backup file found"
        exit 1
    fi
    
    echo "Using: $BACKUP_FILE"
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-db$"; then
        echo "❌ PostgreSQL not running"
        exit 1
    fi
    
    DB_NAME=${DB_NAME:-claimlens}
    DB_USER=${DB_USER:-postgres}
    
    docker cp "$BACKUP_FILE" ${CONTAINER_PREFIX}-db:/tmp/restore.dump
    docker exec ${CONTAINER_PREFIX}-db psql -U "$DB_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" 2>/dev/null || true
    docker exec ${CONTAINER_PREFIX}-db psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null
    docker exec ${CONTAINER_PREFIX}-db psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null
    docker exec ${CONTAINER_PREFIX}-db pg_restore -U "$DB_USER" -d "$DB_NAME" /tmp/restore.dump 2>/dev/null || true
    
    echo "✅ Database restored"
    docker restart ${CONTAINER_PREFIX}-backend 2>/dev/null || true
}

# Function to clean everything
clean_all() {
    echo "🧹 $PROJECT_NAME Docker Clean (Vessel Mode)"
    echo "============================================="
    echo ""
    echo "⚠️  This will stop all containers and remove all data!"
    read -p "Are you sure? (yes/no): " -r
    echo
    
    if [[ $REPLY =~ ^[Yy]es$ ]]; then
        setup_vessel_compat
        
        DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
        
        # Auto-backup
        if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}-db$"; then
            backup_database
        fi
        
        $DOCKER_COMPOSE_CMD down -v --remove-orphans
        echo "✅ Cleanup completed"
    else
        echo "❌ Cancelled"
    fi
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
    restore)
        restore_database "$@"
        ;;
    clean)
        clean_all
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ Unknown command: $COMMAND"
        show_help
        ;;
esac
