import redis
from analytics.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL)

def cache_set(key: str, value: str, ttl: int = 300):
    redis_client.setex(key, ttl, value)

def cache_get(key: str) -> str | None:
    return redis_client.get(key)