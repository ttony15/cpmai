from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

from src.api import api_router
from src.core.settings import settings
from src.infra.db.mongo.engine import init_beanine_db  # noqa


@asynccontextmanager
async def lifespan(
        app: FastAPI,
        **kwargs,
):
    # await init_beanine_db()
    yield


def get_application() -> FastAPI:
    app = FastAPI(
        title=settings.title,
        debug=settings.debug,
        description=settings.description,
        # In production, the docs should be disabled
        # And controlled by our endpoints
        docs_url=None if not settings.debug else settings.docs_url,
        redoc_url=None if not settings.debug else settings.redoc_url,
        openapi_url=None if not settings.debug else settings.openapi_url,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router=api_router)

    # Mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")

    return app
