#!/bin/bash

# =============================================================================
# ClaimLens Scripts Runner
# =============================================================================
# Unified script to run all ClaimLens backend scripts with proper environment setup.
# Supports both local development and Docker container execution.
#
# SCRIPT SUMMARIES:
# =================
#
# RAG SCRIPTS (Python):
# ---------------------
# test_retrieval.py - Tests the hybrid retrieval system with sample insurance queries.
#                     Loads ICICI & Niva Bupa policy documents, splits them into clauses,
#                     builds FAISS index, and retrieves relevant clauses for queries.
#
# run_evaluation.py - Runs evaluation metrics (Recall@K, MRR, etc.) on the retrieval
#                     system using a benchmark query set from evaluation_queries.json.
#                     Reports retrieval accuracy and performance metrics.
#
# export_clauses.py - Exports all extracted policy clauses to a JSON file for
#                     inspection, debugging, or use in other systems.
#                     Output: data/all_clauses.json
#
# main.py           - Basic clause extraction script that demonstrates the
#                     clause-based splitting from policy PDFs. Shows extracted
#                     clauses with metadata and analyzes quality.
#
# INFRASTRUCTURE SCRIPTS:
# -----------------------
# init-db.sql       - PostgreSQL database initialization script. Creates required
#                     extensions (uuid-ossp, vector) and sets up schemas.
#                     Runs automatically on first database container start.
#
# init-localstack.sh - LocalStack initialization script. Creates S3 bucket
#                      'claimlens-documents' with versioning and CORS config.
#                      Runs automatically when LocalStack container starts.
#
# Usage: ./run_rag.sh [command] [options]
# =============================================================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$BACKEND_DIR/.." && pwd)"
DATA_DIR="$PROJECT_ROOT/data"
MODELS_DIR="$PROJECT_ROOT/models"
FAISS_INDEX_DIR="$BACKEND_DIR/faiss_claimlens_index"
FAISS_COMBINED_INDEX_DIR="$BACKEND_DIR/faiss_claimlens_combined_index"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║              ClaimLens Scripts Runner                            ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_help() {
    print_header
    echo -e "${CYAN}Usage:${NC} ./run_rag.sh [command] [options]"
    echo ""
    echo -e "${CYAN}RAG Commands:${NC}"
    echo ""
    echo -e "  ${GREEN}test${NC}        Run retrieval test with sample queries"
    echo "              Tests hybrid retrieval (Dense + BM25) on insurance queries"
    echo "              Script: test_retrieval.py"
    echo ""
    echo -e "  ${GREEN}eval${NC}        Run full evaluation on benchmark queries"
    echo "              Calculates Recall@K, MRR, and other retrieval metrics"
    echo "              Script: run_evaluation.py"
    echo ""
    echo -e "  ${GREEN}export${NC}      Export all clauses to JSON file"
    echo "              Outputs to data/all_clauses.json"
    echo "              Script: export_clauses.py"
    echo ""
    echo -e "  ${GREEN}main${NC}        Run basic clause extraction demo"
    echo "              Demonstrates clause splitting from policy PDFs"
    echo "              Script: main.py"
    echo ""
    echo -e "  ${GREEN}build${NC}       Build/rebuild FAISS vector index"
    echo "              Regenerates embeddings for all policy documents"
    echo ""
    echo -e "${CYAN}Infrastructure Commands:${NC}"
    echo ""
    echo -e "  ${GREEN}init-db${NC}     Show database initialization SQL"
    echo "              Script: init-db.sql"
    echo ""
    echo -e "  ${GREEN}init-s3${NC}     Initialize LocalStack S3 bucket"
    echo "              Script: init-localstack.sh"
    echo ""
    echo -e "${CYAN}Execution Commands:${NC}"
    echo ""
    echo -e "  ${GREEN}docker${NC} [cmd] Run command inside Docker container"
    echo "              Usage: ./run_rag.sh docker [test|eval|export|main]"
    echo ""
    echo -e "  ${GREEN}list${NC}        List all available scripts with descriptions"
    echo ""
    echo -e "  ${GREEN}status${NC}      Check RAG system status and configuration"
    echo ""
    echo -e "  ${GREEN}help${NC}        Show this help message"
    echo ""
    echo -e "${CYAN}Options:${NC}"
    echo "  --verbose       Enable verbose output"
    echo "  --policy=NAME   Run on specific policy (icici, niva, both)"
    echo "  --top-k=N       Number of results to retrieve (default: 5)"
    echo ""
    echo -e "${CYAN}Examples:${NC}"
    echo "  ./run_rag.sh test                  # Test retrieval locally"
    echo "  ./run_rag.sh docker test           # Test retrieval in Docker"
    echo "  ./run_rag.sh eval --verbose        # Run evaluation with details"
    echo "  ./run_rag.sh build --policy=icici  # Rebuild index for ICICI only"
    echo "  ./run_rag.sh list                  # List all scripts"
    echo "  ./run_rag.sh status                # Check system status"
    echo ""
    echo -e "${CYAN}Environment Variables:${NC}"
    echo "  EMBEDDING_MODEL_SIZE   Model size: small, base, large (default: base)"
    echo "  USE_RERANKER           Enable cross-encoder reranking: true/false"
    echo "  DENSE_TOP_K            Dense retrieval top-k (default: 20)"
    echo ""
}

list_scripts() {
    print_header
    echo -e "${CYAN}Available Scripts:${NC}"
    echo ""
    echo -e "${MAGENTA}RAG Pipeline Scripts (Python):${NC}"
    echo ""
    echo -e "  ${GREEN}test_retrieval.py${NC}"
    echo "    Purpose: Tests hybrid retrieval with sample insurance queries"
    echo "    Input:   Policy PDFs (data/*.pdf)"
    echo "    Output:  Retrieved clauses with relevance scores"
    echo "    Command: ./run_rag.sh test"
    echo ""
    echo -e "  ${GREEN}run_evaluation.py${NC}"
    echo "    Purpose: Runs evaluation metrics on retrieval system"
    echo "    Input:   data/evaluation_queries.json (benchmark queries)"
    echo "    Output:  Recall@K, MRR, Precision@K metrics"
    echo "    Command: ./run_rag.sh eval"
    echo ""
    echo -e "  ${GREEN}export_clauses.py${NC}"
    echo "    Purpose: Exports extracted clauses to JSON"
    echo "    Input:   Policy PDFs (data/*.pdf)"
    echo "    Output:  data/all_clauses.json"
    echo "    Command: ./run_rag.sh export"
    echo ""
    echo -e "  ${GREEN}main.py${NC}"
    echo "    Purpose: Demonstrates clause extraction pipeline"
    echo "    Input:   data/icici_complete_health.pdf"
    echo "    Output:  Clause analysis and quality metrics"
    echo "    Command: ./run_rag.sh main"
    echo ""
    echo -e "${MAGENTA}Infrastructure Scripts:${NC}"
    echo ""
    echo -e "  ${GREEN}init-db.sql${NC}"
    echo "    Purpose: PostgreSQL database initialization"
    echo "    Creates: uuid-ossp extension, vector extension, schemas"
    echo "    Runs:    Automatically on first DB container start"
    echo "    Command: ./run_rag.sh init-db"
    echo ""
    echo -e "  ${GREEN}init-localstack.sh${NC}"
    echo "    Purpose: LocalStack S3 bucket setup"
    echo "    Creates: claimlens-documents bucket with CORS"
    echo "    Runs:    Automatically on LocalStack container start"
    echo "    Command: ./run_rag.sh init-s3"
    echo ""
}

print_status() {
    print_header
    echo -e "${CYAN}System Status:${NC}"
    echo ""
    
    # Check Python
    echo -n "  Python3:           "
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        echo -e "${GREEN}✓${NC} $PYTHON_VERSION"
    else
        echo -e "${RED}✗ Not found${NC}"
    fi
    
    # Check data directory
    echo -n "  Data Dir:          "
    if [[ -d "$DATA_DIR" ]]; then
        PDF_COUNT=$(find "$DATA_DIR" -name "*.pdf" 2>/dev/null | wc -l | tr -d ' ')
        echo -e "${GREEN}✓${NC} Found ($PDF_COUNT PDF files)"
    else
        echo -e "${RED}✗ Not found${NC}"
    fi
    
    # Check models directory
    echo -n "  Models Dir:        "
    if [[ -d "$MODELS_DIR" && -n "$(ls -A "$MODELS_DIR" 2>/dev/null)" ]]; then
        MODEL_COUNT=$(find "$MODELS_DIR" -maxdepth 1 -type d | wc -l | tr -d ' ')
        echo -e "${GREEN}✓${NC} Found ($((MODEL_COUNT - 1)) models)"
    else
        echo -e "${YELLOW}⚠${NC} Not found or empty (will download on first run)"
    fi
    
    # Check FAISS index
    echo -n "  FAISS Index:       "
    if [[ -d "$FAISS_INDEX_DIR" && -f "$FAISS_INDEX_DIR/index.faiss" ]]; then
        INDEX_SIZE=$(du -h "$FAISS_INDEX_DIR/index.faiss" 2>/dev/null | cut -f1)
        echo -e "${GREEN}✓${NC} Found ($INDEX_SIZE)"
    elif [[ -d "$FAISS_COMBINED_INDEX_DIR" && -f "$FAISS_COMBINED_INDEX_DIR/index.faiss" ]]; then
        INDEX_SIZE=$(du -h "$FAISS_COMBINED_INDEX_DIR/index.faiss" 2>/dev/null | cut -f1)
        echo -e "${GREEN}✓${NC} Combined index found ($INDEX_SIZE)"
    else
        echo -e "${YELLOW}⚠${NC} Not built (run ./run_rag.sh build)"
    fi
    
    # Check evaluation queries
    echo -n "  Eval Queries:      "
    if [[ -f "$DATA_DIR/evaluation_queries.json" ]]; then
        QUERY_COUNT=$(python3 -c "import json; print(len(json.load(open('$DATA_DIR/evaluation_queries.json'))))" 2>/dev/null || echo "?")
        echo -e "${GREEN}✓${NC} Found ($QUERY_COUNT queries)"
    else
        echo -e "${YELLOW}⚠${NC} Not found (needed for eval)"
    fi
    
    # Check exported clauses
    echo -n "  Exported Clauses:  "
    if [[ -f "$DATA_DIR/all_clauses.json" ]]; then
        CLAUSE_COUNT=$(python3 -c "import json; d=json.load(open('$DATA_DIR/all_clauses.json')); print(len(d.get('clauses', d)))" 2>/dev/null || echo "?")
        echo -e "${GREEN}✓${NC} Found ($CLAUSE_COUNT clauses)"
    else
        echo -e "${YELLOW}⚠${NC} Not exported (run ./run_rag.sh export)"
    fi
    
    # Check Docker
    echo -n "  Docker Backend:    "
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "claimlens-backend"; then
        echo -e "${GREEN}✓${NC} Container running"
    else
        echo -e "${YELLOW}⚠${NC} Container not running"
    fi
    
    echo -n "  Docker LocalStack: "
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "claimlens-localstack"; then
        echo -e "${GREEN}✓${NC} Container running"
    else
        echo -e "${YELLOW}⚠${NC} Container not running"
    fi
    
    echo -n "  Docker Database:   "
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "claimlens-db"; then
        echo -e "${GREEN}✓${NC} Container running"
    else
        echo -e "${YELLOW}⚠${NC} Container not running"
    fi
    
    echo ""
    echo -e "${CYAN}Configuration:${NC}"
    echo "  EMBEDDING_MODEL_SIZE:  ${EMBEDDING_MODEL_SIZE:-base}"
    echo "  USE_RERANKER:          ${USE_RERANKER:-false}"
    echo "  DENSE_TOP_K:           ${DENSE_TOP_K:-20}"
    echo ""
    echo -e "${CYAN}Scripts Directory:${NC} $SCRIPT_DIR"
    echo ""
    echo "  Available scripts:"
    ls -la "$SCRIPT_DIR"/*.py "$SCRIPT_DIR"/*.sql "$SCRIPT_DIR"/*.sh 2>/dev/null | awk '{print "    " $NF}'
    echo ""
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: python3 is not installed or not in PATH${NC}"
        echo ""
        echo "Please install Python 3.11+ to run these scripts."
        exit 1
    fi
}

check_dependencies() {
    echo -e "${CYAN}Checking dependencies...${NC}"
    
    # Check if required packages are installed
    python3 -c "import langchain_huggingface" 2>/dev/null || {
        echo -e "${YELLOW}Warning: langchain_huggingface not installed${NC}"
        echo "Run: pip install langchain-huggingface"
    }
    
    python3 -c "import faiss" 2>/dev/null || {
        echo -e "${YELLOW}Warning: faiss not installed${NC}"
        echo "Run: pip install faiss-cpu"
    }
    
    python3 -c "import torch" 2>/dev/null || {
        echo -e "${YELLOW}Warning: torch not installed${NC}"
        echo "Run: pip install torch"
    }
}

# Run a Python script with proper PYTHONPATH and environment
run_script() {
    local script_name=$1
    shift
    local extra_args="$@"
    
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Running: ${script_name}${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Set environment variables
    export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"
    export DATA_DIR="$DATA_DIR"
    export MODELS_DIR="$MODELS_DIR"
    export HF_HOME="$MODELS_DIR"
    export TRANSFORMERS_CACHE="$MODELS_DIR"
    export EMBEDDING_MODEL_SIZE="${EMBEDDING_MODEL_SIZE:-base}"
    export USE_RERANKER="${USE_RERANKER:-false}"
    export DENSE_TOP_K="${DENSE_TOP_K:-20}"
    
    # Run the script
    local start_time=$(date +%s)
    python3 "$BACKEND_DIR/scripts/$script_name" $extra_args
    local exit_code=$?
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo ""
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ Script completed successfully in ${duration}s${NC}"
    else
        echo -e "${RED}✗ Script failed with exit code: $exit_code${NC}"
    fi
    
    return $exit_code
}

# Run script inside Docker container
run_docker() {
    local script_name=$1
    shift
    
    if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "claimlens-backend"; then
        echo -e "${RED}Error: Backend container is not running${NC}"
        echo ""
        echo "Start the container first with:"
        echo "  ./docker-manage.sh start local"
        exit 1
    fi
    
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Running in Docker: ${script_name}${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    docker exec -it claimlens-backend python3 /app/scripts/$script_name "$@"
}

# Show database initialization SQL
show_init_db() {
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Database Initialization Script: init-db.sql${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${CYAN}Purpose:${NC}"
    echo "  This SQL script runs automatically when the PostgreSQL container"
    echo "  starts for the first time. It sets up required extensions."
    echo ""
    echo -e "${CYAN}Contents:${NC}"
    echo ""
    cat "$SCRIPT_DIR/init-db.sql"
    echo ""
    echo -e "${CYAN}To run manually in database:${NC}"
    echo "  docker exec -it claimlens-db psql -U postgres -d claimlens -f /docker-entrypoint-initdb.d/init.sql"
    echo ""
}

# Run LocalStack initialization
run_init_s3() {
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}LocalStack S3 Initialization: init-localstack.sh${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "claimlens-localstack"; then
        echo -e "${RED}Error: LocalStack container is not running${NC}"
        echo ""
        echo "Start the container first with:"
        echo "  ./docker-manage.sh start local"
        exit 1
    fi
    
    echo -e "${CYAN}Running initialization script in LocalStack container...${NC}"
    echo ""
    docker exec -it claimlens-localstack /etc/localstack/init/ready.d/init.sh
    echo ""
    echo -e "${GREEN}✓ LocalStack S3 initialization complete${NC}"
}

# Build FAISS index
build_index() {
    echo -e "${CYAN}Building FAISS vector index...${NC}"
    echo ""
    
    # Check for policy documents
    if [[ ! -d "$DATA_DIR" ]] || [[ -z "$(find "$DATA_DIR" -name "*.pdf" 2>/dev/null)" ]]; then
        echo -e "${RED}Error: No PDF files found in $DATA_DIR${NC}"
        exit 1
    fi
    
    # Create the build script dynamically
    cat > /tmp/build_index.py << 'EOFSCRIPT'
#!/usr/bin/env python3
"""Build FAISS index for policy documents."""
import os
import sys

# Setup paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get('BACKEND_DIR', SCRIPT_DIR))

from app.retriever.embeddings import load_embedding_model
from app.retriever.vector_store import build_or_load_vectorstore
from app.ingestion.clause_splitter import clause_based_splitter
from app.ingestion.loader import load_policy_documents

DATA_DIR = os.environ.get('DATA_DIR', '../data')
INDEX_PATH = os.environ.get('FAISS_INDEX_PATH', 'faiss_claimlens_combined_index')
MODEL_SIZE = os.environ.get('EMBEDDING_MODEL_SIZE', 'base')

print(f"Data directory: {DATA_DIR}")
print(f"Index path: {INDEX_PATH}")
print(f"Model size: {MODEL_SIZE}")
print()

# Load documents
all_docs = []

# Load ICICI docs
icici_path = os.path.join(DATA_DIR, "icici_complete_health.pdf")
if os.path.exists(icici_path):
    print("Loading ICICI Complete Health policy...")
    docs = load_policy_documents(
        pdf_path=icici_path,
        insurer="ICICI Lombard",
        policy_name="Complete Health Insurance",
        uin="ICIHLIP25035V082425",
        policy_version_year=2025
    )
    all_docs.extend(docs)
    print(f"  Loaded {len(docs)} pages")

# Load Niva docs
niva_path = os.path.join(DATA_DIR, "niva_rise.pdf")
if os.path.exists(niva_path):
    print("Loading Niva Bupa Rise policy...")
    docs = load_policy_documents(
        pdf_path=niva_path,
        insurer="Niva Bupa",
        policy_name="Rise Policy",
        uin="NIVHLIPXXXX",
        policy_version_year=2025
    )
    all_docs.extend(docs)
    print(f"  Loaded {len(docs)} pages")

if not all_docs:
    print("Error: No documents loaded!")
    sys.exit(1)

print(f"\nTotal pages loaded: {len(all_docs)}")

# Split into clauses
print("\nSplitting into clauses...")
clauses = clause_based_splitter(all_docs)
print(f"Total clauses extracted: {len(clauses)}")

# Load embedding model
print(f"\nLoading embedding model (size={MODEL_SIZE})...")
embedding_model = load_embedding_model(model_size=MODEL_SIZE)

# Build vector store (this will save to disk)
print("\nBuilding FAISS index...")
# Force rebuild by removing existing index
if os.path.exists(INDEX_PATH):
    import shutil
    shutil.rmtree(INDEX_PATH)

vectorstore = build_or_load_vectorstore(
    clause_documents=clauses,
    embedding_model=embedding_model,
    index_path=INDEX_PATH
)

print(f"\n✓ FAISS index built successfully at: {INDEX_PATH}")
EOFSCRIPT
    
    export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"
    export DATA_DIR="$DATA_DIR"
    export BACKEND_DIR="$BACKEND_DIR"
    export FAISS_INDEX_PATH="$BACKEND_DIR/faiss_claimlens_combined_index"
    export EMBEDDING_MODEL_SIZE="${EMBEDDING_MODEL_SIZE:-base}"
    export HF_HOME="$MODELS_DIR"
    export TRANSFORMERS_CACHE="$MODELS_DIR"
    
    python3 /tmp/build_index.py
    rm -f /tmp/build_index.py
}

# =============================================================================
# Main Script Logic
# =============================================================================

main() {
    # Parse options
    VERBOSE=false
    POLICY="both"
    TOP_K=5
    
    for arg in "$@"; do
        case $arg in
            --verbose)
                VERBOSE=true
                shift
                ;;
            --policy=*)
                POLICY="${arg#*=}"
                shift
                ;;
            --top-k=*)
                TOP_K="${arg#*=}"
                shift
                ;;
        esac
    done
    
    # Export options as environment variables
    export VERBOSE
    export POLICY
    export TOP_K
    
    case "${1:-help}" in
        # RAG Commands
        test)
            check_python
            run_script "test_retrieval.py"
            ;;
        eval)
            check_python
            run_script "run_evaluation.py"
            ;;
        export)
            check_python
            run_script "export_clauses.py"
            ;;
        main)
            check_python
            run_script "main.py"
            ;;
        build)
            check_python
            build_index
            ;;
        # Infrastructure Commands
        init-db)
            show_init_db
            ;;
        init-s3|init-localstack)
            run_init_s3
            ;;
        # Docker execution
        docker)
            shift
            case "${1:-help}" in
                test)
                    run_docker "test_retrieval.py"
                    ;;
                eval)
                    run_docker "run_evaluation.py"
                    ;;
                export)
                    run_docker "export_clauses.py"
                    ;;
                main)
                    run_docker "main.py"
                    ;;
                *)
                    echo -e "${RED}Unknown docker command: $1${NC}"
                    echo "Available: test, eval, export, main"
                    exit 1
                    ;;
            esac
            ;;
        # Utility Commands
        list)
            list_scripts
            ;;
        status)
            print_status
            ;;
        help|--help|-h)
            print_help
            ;;
        *)
            echo -e "${RED}Unknown command: $1${NC}"
            echo ""
            print_help
            exit 1
            ;;
    esac
}

main "$@"
