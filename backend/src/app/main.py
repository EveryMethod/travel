"""FastAPI application entrypoint."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from src.app.api.router import api_router
from src.app.core.config import settings

logger = logging.getLogger(__name__)
SERVICE_UNAVAILABLE_DETAIL = "服务暂时繁忙，请稍后重试。"

app = FastAPI(title=settings.app_name)


@app.exception_handler(RedisError)
def redis_error_handler(request: Request, exc: RedisError) -> JSONResponse:
    logger.error("Redis service unavailable", exc_info=exc)
    return JSONResponse(status_code=503, content={"detail": SERVICE_UNAVAILABLE_DETAIL})


@app.exception_handler(SQLAlchemyError)
def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("Database service unavailable", exc_info=exc)
    return JSONResponse(status_code=503, content={"detail": SERVICE_UNAVAILABLE_DETAIL})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
