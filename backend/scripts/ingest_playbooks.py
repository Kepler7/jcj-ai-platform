import json
import os
import uuid
import chromadb

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))
COLLECTION = os.getenv("CHROMA_COLLECTION", "jcj_playbooks_v1")
PATH = os.getenv("PLAYBOOK_PATH", "data/playbooks/playbooks.normalized.jsonl")


def _to_int(x, default: int) -> int:
    try:
        if x is None:
            return default
        if isinstance(x, bool):
            return default
        return int(x)
    except Exception:
        return default


def _to_str(x) -> str:
    return "" if x is None else str(x)


def _delete_all_by_ids(col, batch_size: int = 2000) -> int:
    """
    Chroma 1.3.x:
    - get() siempre regresa 'ids' en el payload, pero 'ids' NO es válido en include=[]
    - delete(where={}) no permitido
    => borramos todo por ids en batches
    """
    total_deleted = 0

    while True:
        res = col.get(limit=batch_size)  # no include
        ids = res.get("ids") or []
        if not ids:
            break

        col.delete(ids=ids)
        total_deleted += len(ids)

    return total_deleted


def main():
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    col = client.get_or_create_collection(COLLECTION)

    # 1) Limpieza total (por ids)
    deleted = _delete_all_by_ids(col)
    print("CLEARED deleted=", deleted, "count_now=", col.count())

    # 2) Cargar docs + metadatas
    ids = []
    docs = []
    metas = []

    with open(PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)

            pb_id = _to_str(obj.get("id") or uuid.uuid4().hex)
            doc = json.dumps(obj, ensure_ascii=False)

            age_min = _to_int(obj.get("age_min"), 0)
            age_max = _to_int(obj.get("age_max"), 99)

            meta = {
                "source": _to_str(obj.get("source", "sheet")),
                "topic_nucleo": _to_str(obj.get("topic_nucleo", ""))[:200],
                "subskill": _to_str(obj.get("subskill", ""))[:200],
                "age_min": age_min,
                "age_max": age_max,
            }

            ids.append(pb_id)
            docs.append(doc)
            metas.append(meta)

    col.upsert(ids=ids, documents=docs, metadatas=metas)
    print("DONE. collection=", COLLECTION, "count=", col.count())


if __name__ == "__main__":
    main()
