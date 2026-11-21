from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.services.health import readiness

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: the process is up. Touches no dependencies."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    """Readiness: dependencies reachable. 503 tells a load balancer to stop routing here."""
    checks = await readiness(request.app.state.engine, request.app.state.redis)
    ok = all(checks.values())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ready" if ok else "degraded", "checks": checks},
    )
