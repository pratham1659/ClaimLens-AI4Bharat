
# backend/app/api/v1/router.py
"""
API v1 router aggregating all endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, claims, documents, analysis, policies

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(claims.router)
api_router.include_router(documents.router)
api_router.include_router(analysis.router)
api_router.include_router(policies.router)
