from fastapi import APIRouter

from app.api.v1 import audit_logs, auth, services, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(services.router)
api_router.include_router(audit_logs.router)
