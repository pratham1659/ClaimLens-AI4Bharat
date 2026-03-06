# backend/app/main.py
"""
FastAPI application entry point.
"""

import logging
import os
import base64
import binascii
import secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from starlette.exceptions import HTTPException as StarletteHTTPException
import time
import uuid

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import (
    ClaimLensException,
    claimlens_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    unhandled_exception_handler
)
from app.api.v1.router import api_router
from app.db.init_db import init_db

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Log RAG configuration
    use_mock_llm = os.getenv("USE_MOCK_LLM", "false").lower() == "true"
    bedrock_enabled = os.getenv("BEDROCK_ENABLED", "true").lower() == "true"
    embedding_mode = os.getenv("EMBEDDING_MODE", "auto")

    logger.info(f"RAG Configuration:")
    logger.info(f"  - USE_MOCK_LLM: {use_mock_llm}")
    logger.info(f"  - BEDROCK_ENABLED: {bedrock_enabled}")
    logger.info(f"  - EMBEDDING_MODE: {embedding_mode}")

    if use_mock_llm or not bedrock_enabled:
        logger.info(
            "  - Mode: LOCAL DEVELOPMENT (HuggingFace embeddings, Mock LLM)")
    else:
        logger.info("  - Mode: PRODUCTION (AWS Bedrock embeddings and LLM)")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

    # Pre-load embedding model in local mode for faster first request
    if use_mock_llm or not bedrock_enabled:
        try:
            from app.rag.embeddings import get_embedding_service
            embedding_service = get_embedding_service()
            logger.info(f"Embedding service initialized: mode={embedding_service.mode}, "
                        f"dimension={embedding_service.embedding_dimension}")
        except Exception as e:
            logger.warning(
                f"Could not pre-initialize embedding service: {str(e)}")

    yield

    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI application
app = FastAPI(
    title="ClaimLens AI",
    version=settings.APP_VERSION,
    description="""
# ClaimLens AI - Medical Insurance Compliance Platform

AI-powered platform for analyzing medical insurance claims and ensuring compliance.

## Features

- **Claim Management**: Create, view, and manage insurance claims
- **Document Processing**: Upload and process medical documents (discharge summaries, policies, billing data)
- **AI Analysis**: Get AI-powered compliance analysis using AWS Bedrock Claude models
- **Policy Search**: Vector-based semantic search across policy documents
- **User Authentication**: JWT-based authentication with role-based access control

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get access token
- `GET /api/v1/auth/me` - Get current user info

### Claims
- `GET /api/v1/claims` - List all claims
- `POST /api/v1/claims` - Create new claim
- `GET /api/v1/claims/{id}` - Get claim details
- `DELETE /api/v1/claims/{id}` - Delete claim

### Documents
- `POST /api/v1/documents/upload` - Upload document to claim
- `GET /api/v1/documents/{id}` - Get document details
- `DELETE /api/v1/documents/{id}` - Delete document

### Analysis
- `POST /api/v1/analysis/analyze/{claim_id}` - Run AI compliance analysis
- `GET /api/v1/analysis/results/{claim_id}` - Get analysis results

### Policies
- `POST /api/v1/policies/search` - Semantic search across policies
    """,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Health", "description": "Health check endpoints"},
        {"name": "Root", "description": "Root information"},
        {"name": "Authentication", "description": "User authentication and authorization"},
        {"name": "Claims", "description": "Insurance claim management"},
        {"name": "Documents", "description": "Document upload and processing"},
        {"name": "Analysis", "description": "AI-powered compliance analysis"},
        {"name": "Policies", "description": "Policy search and management"},
    ],
    swagger_ui_parameters={
        "docExpansion": "list",
        "defaultModelsExpandDepth": 3,
        "syntaxHighlight.theme": "obsidian",
    }
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing."""
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    # Add request ID to state
    request.state.request_id = request_id

    # Process request
    try:
        response = await call_next(request)
    except Exception:
        duration = time.time() - start_time
        logger.exception(
            "Request failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": round(duration * 1000, 2)
            }
        )
        raise

    # Calculate duration
    duration = time.time() - start_time

    # Log request
    logger.info(
        f"Request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2)
        }
    )

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    return response


def _unauthorized_docs_response() -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "detail": "Authentication required for API docs."
        },
        headers={"WWW-Authenticate": 'Basic realm="ClaimLens API Docs"'},
    )


async def enforce_docs_auth(request: Request):
    docs_paths = {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}
    if request.url.path not in docs_paths:
        return None

    docs_username = os.getenv("DOCS_AUTH_USERNAME", "admin")
    docs_password = os.getenv("DOCS_AUTH_PASSWORD", "admin")

    authorization = request.headers.get("Authorization", "")
    if not authorization.lower().startswith("basic "):
        return _unauthorized_docs_response()

    encoded_credentials = authorization.split(" ", 1)[1].strip()
    if not encoded_credentials:
        return _unauthorized_docs_response()

    try:
        decoded = base64.b64decode(encoded_credentials).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return _unauthorized_docs_response()

    if ":" not in decoded:
        return _unauthorized_docs_response()

    username, password = decoded.split(":", 1)

    valid_username = secrets.compare_digest(username, docs_username)
    valid_password = secrets.compare_digest(password, docs_password)

    if not (valid_username and valid_password):
        return _unauthorized_docs_response()

    return None


@app.middleware("http")
async def docs_auth_middleware(request: Request, call_next):
    response = await enforce_docs_auth(request)
    if response:
        return response
    return await call_next(request)


# Exception handlers
app.add_exception_handler(ClaimLensException, claimlens_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    """
    from datetime import datetime

    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "health": "/health",
        "api": settings.API_V1_PREFIX
    }


@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )


@app.get("/docs", include_in_schema=False)
async def get_documentation():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - Swagger UI",
    )


@app.get("/redoc", include_in_schema=False)
async def get_redoc_documentation():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - ReDoc",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else 4
    )
