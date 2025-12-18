import os
import redis

REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    raise RuntimeError("REDIS_URL is not set")

client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def ping_redis() -> None:
    """Raises exception if Redis is not reachable."""
    client.ping()
