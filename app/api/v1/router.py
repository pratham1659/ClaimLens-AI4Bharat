from fastapi import APIRouter

from app.api.v1.routes import admin, claims, documents, evaluation, health, policies


api_v1_router = APIRouter()
api_v1_router.include_router(health.router, tags=["health"])
api_v1_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_v1_router.include_router(policies.router, prefix="/policies", tags=["policies"])
api_v1_router.include_router(claims.router, prefix="/claims", tags=["claims"])
api_v1_router.include_router(evaluation.router, prefix="/evaluation", tags=["evaluation"])
api_v1_router.include_router(admin.router, prefix="/admin", tags=["admin"])
