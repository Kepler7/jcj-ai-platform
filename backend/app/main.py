from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .db import ping_db
from .cache import ping_redis

from .logging_config import configure_logging
configure_logging()


app = FastAPI(title="JCJ AI Platform")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/health/deps")
def health_deps():
    results = {
        "postgres": {"ok": False, "error": None},
        "redis": {"ok": False, "error": None},
    }

    # Check Postgres
    try:
        ping_db()
        results["postgres"]["ok"] = True
    except Exception as e:
        results["postgres"]["error"] = str(e)

    # Check Redis
    try:
        ping_redis()
        results["redis"]["ok"] = True
    except Exception as e:
        results["redis"]["error"] = str(e)

    all_ok = results["postgres"]["ok"] and results["redis"]["ok"]

    if all_ok:
        return {"status": "ok", "deps": results}

    return JSONResponse(
        status_code=503,
        content={"status": "degraded", "deps": results},
    )

