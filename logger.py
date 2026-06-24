from fastapi import FastAPI

from src.api.routes import router
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI Autonomous DevOps & SDLC Platform - Sprint 1 Foundation",
)

app.include_router(router)


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)
