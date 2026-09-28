"""
Sentinel — FastAPI Application Entry Point.
"""

from __future__ import annotations
from contextlib import asynccontextmanager

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.config import settings
from app.core.database import engine, AsyncSessionFactory
from app.services.detection_service import DetectionService
from app.api.v1 import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):

    print("=" * 60)
    print("Sentinel AI Started")
    print("=" * 60)

    yield

    await engine.dispose()


def create_app() -> FastAPI:

    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-Based Video Surveillance & Emergency Response System",
        version="1.0.0",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "environment": settings.APP_ENV,
        }

    @app.post("/api/v1/inference", tags=["Inference"])
    async def run_inference():
        return {"status": "processing"}

    # Register all API v1 routes
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()