import os
from redis import Redis
from rq import Queue

def get_redis() -> Redis:
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    return Redis.from_url(redis_url)

def get_queue() -> Queue:
    return Queue("jcj", connection=get_redis())