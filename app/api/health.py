from fastapi import APIRouter, Response, status
from app.config import settings
from app.database.session import check_db_health

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness():
    """Liveness probe: verifies web server is up and responsive."""
    return {"status": "live", "app_env": settings.APP_ENV}


@router.get("/ready")
async def readiness(response: Response):
    """Readiness probe: verifies essential dependencies (e.g. database connectivity)."""
    db_ok = await check_db_health()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unready", "database": "disconnected"}

    return {
        "status": "ready",
        "database": "connected",
        "is_postgres": settings.is_postgres,
    }
