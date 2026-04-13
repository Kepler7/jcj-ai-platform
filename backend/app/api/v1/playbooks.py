from fastapi import APIRouter, Depends, HTTPException, Query
import os

from app.ai.orchestrator import parse_playbook_doc_v2
from app.auth.deps import get_current_user, require_role
from app.rag.chroma_client import ChromaPlaybookStore
from app.modules.playbooks.queue import enqueue_playbook_sync, get_job_status

from app.db.session import get_db_session
from app.modules.playbooks.sync_runs_service import (
    get_latest_sync_run,
    serialize_sync_run,
)

router = APIRouter(prefix="/v1/playbooks", tags=["playbooks"])

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "jcj_playbooks_v1")


def _load_all_playbooks_index():
    store = ChromaPlaybookStore(
        host=CHROMA_HOST,
        port=CHROMA_PORT,
        collection_name=CHROMA_COLLECTION,
    )

    result = (
        store.query(
            query_text="playbook",
            age=None,
            n_results=200,
        )
        or {}
    )

    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []

    if metadatas and isinstance(metadatas[0], list):
        metadatas = metadatas[0]

    index = {}

    for i, doc in enumerate(documents):
        md = metadatas[i] if i < len(metadatas) else {}
        pb_id = str(md.get("id") or "").strip()

        if not pb_id:
            continue

        parsed = parse_playbook_doc_v2(doc)
        if not parsed:
            continue

        parsed["id"] = pb_id
        parsed["base_row"] = str(
            md.get("base_row") or parsed.get("base_row") or ""
        ).strip()

        index[pb_id] = parsed

    return index


def _to_preview(pb: dict):
    return {
        "id": str(pb.get("id") or ""),
        "topic_nucleo": pb.get("topic_nucleo"),
        "subhabilidad": pb.get("subhabilidad"),
        "senal_observable": pb.get("senal_observable"),
        "age_min": pb.get("age_min"),
        "age_max": pb.get("age_max"),
    }


@router.get("/search")
def search_playbooks(
    q: str = Query(..., min_length=2),
    limit: int = Query(default=10, ge=1, le=30),
    current_user=Depends(get_current_user),
):
    require_role(current_user, ["platform_admin", "school_admin", "teacher"])

    store = ChromaPlaybookStore(
        host=CHROMA_HOST,
        port=CHROMA_PORT,
        collection_name=CHROMA_COLLECTION,
    )

    result = (
        store.query(
            query_text=q,
            age=None,
            n_results=limit,
        )
        or {}
    )

    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []

    if metadatas and isinstance(metadatas[0], list):
        metadatas = metadatas[0]

    out = []

    for i, doc in enumerate(documents):
        md = metadatas[i] if i < len(metadatas) else {}
        pb_id = str(md.get("id") or "").strip()
        if not pb_id:
            continue

        parsed = parse_playbook_doc_v2(doc)
        if not parsed:
            continue

        parsed["id"] = pb_id
        out.append(_to_preview(parsed))

    # dedupe por id
    seen = set()
    deduped = []
    for item in out:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        deduped.append(item)

    return deduped


@router.get("/{playbook_id}")
def get_playbook(
    playbook_id: str,
    current_user=Depends(get_current_user),
):
    require_role(current_user, ["platform_admin", "school_admin", "teacher"])

    index = _load_all_playbooks_index()
    pb = index.get(playbook_id)

    if not pb:
        raise HTTPException(status_code=404, detail="Playbook not found")

    return pb


@router.post("/sync")
def sync_playbooks_endpoint(
    current_user=Depends(get_current_user),
):
    require_role(current_user, ["platform_admin"])

    try:
        job = enqueue_playbook_sync()
        return {
            "ok": True,
            "job_id": job.id,
            "status": job.get_status(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/sync/latest")
def get_latest_sync_endpoint():
    db = get_db_session()
    try:
        run = get_latest_sync_run(db)
        if run is None:
            raise HTTPException(status_code=404, detail="No sync runs found")

        return serialize_sync_run(run)
    finally:
        db.close()


@router.get("/sync/{job_id}")
def get_sync_status_endpoint(job_id: str):
    try:
        return get_job_status(job_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
