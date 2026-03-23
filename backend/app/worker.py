import os
from redis import Redis
from rq import Worker, Queue

listen = ["jcj"]

redis_url = os.getenv("REDIS_URL")
if not redis_url:
    raise RuntimeError("REDIS_URL is not set")

redis_conn = Redis.from_url(
    redis_url,
    socket_connect_timeout=10,
    socket_timeout=30,
    socket_keepalive=True,
    retry_on_timeout=True,
)

queues = [Queue(name, connection=redis_conn) for name in listen]

if __name__ == "__main__":
    worker = Worker(queues, connection=redis_conn)
    worker.work()
