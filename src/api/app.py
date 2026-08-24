from fastapi import FastAPI

from src.api.routes import router


app = FastAPI(
    title="AI Autonomous DevOps Platform API",
    version="1.0.0",
    description=(
        "REST API for AI-assisted DevOps orchestration, "
        "human approvals, execution history, and auditing."
    ),
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "platform": "AI Autonomous DevOps Platform",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }