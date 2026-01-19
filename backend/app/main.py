from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.db.db import ping_db
from .cache import ping_redis

from .logging_config import configure_logging

# 1️⃣ Configura logging (antes de levantar la app)
configure_logging()

# 2️⃣ Crea la app
app = FastAPI(title="JCJ AI Platform")

# 3️⃣ Routers
from app.api.v1.schools import router as schools_router
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.students import router as students_router
from app.api.v1.reports import router as reports_router
from app.api.v1.ai_reports import router as ai_reports_router
from app.api.v1.ai_jobs import router as ai_jobs_router

app.include_router(schools_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(students_router)
app.include_router(reports_router)
app.include_router(ai_reports_router)
app.include_router(ai_jobs_router)

# 4️⃣ Health checks
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

