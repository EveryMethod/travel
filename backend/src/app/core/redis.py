"""Redis client setup."""

from redis import Redis

from src.app.core.config import settings


redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
