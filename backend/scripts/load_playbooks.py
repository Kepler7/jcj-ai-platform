from pathlib import Path
import json

from app.rag.chroma_client import ChromaPlaybookStore


PLAYBOOK_DIR = Path("/app/data/playbooks")
JSONL_FILE = PLAYBOOK_DIR / "playbooks.normalized.jsonl"

COLLECTION_NAME = "jcj_playbooks_v1"


def load_jsonl_playbooks(store: ChromaPlaybookStore):
    if not JSONL_FILE.exists():
        print(f"⚠️ JSONL not found: {JSONL_FILE}")
        return 0

    count = 0
    with JSONL_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            pb = json.loads(line)

            # Texto que irá a embeddings (MUY IMPORTANTE)
            text = f"""
    PROBLEMA: {pb.get("problem_title")}

    EDAD: {pb.get("age_min")}–{pb.get("age_max")}
    TOPIC: {pb.get("topic_nucleo")}
    CONTEXTS: {", ".join(pb.get("contexts", []))}

    COMPORTAMIENTO OBSERVADO:
    {pb.get("behavior")}

    OBJETIVOS:
    - """ + "\n- ".join(pb.get("goal", [])) + """

    ESTRATEGIAS:
    - """ + "\n- ".join(pb.get("strategies", []))

    metadata = {
        "id": pb.get("id"),
        "base_row": pb.get("base_row"),
        "topic_nucleo": pb.get("topic_nucleo"),
        "contexts": pb.get("contexts"),
        "age_min": pb.get("age_min"),
        "age_max": pb.get("age_max"),
        "source": "sheet",
    }

    store.add_document(
        doc_id=metadata["id"],
        text=text.strip(),
        metadata=metadata,
    )
    count += 1

    return count


def main():
    store = ChromaPlaybookStore(
        host="chroma",
        port=8000,
        collection_name=COLLECTION_NAME,
    )

    print("🧹 Clearing existing collection...")
    store.reset()

    print("📥 Loading playbooks from JSONL (sheet)...")
    sheet_count = load_jsonl_playbooks(store)
    print(f"✅ Loaded {sheet_count} playbooks from sheet")

    print("📊 Final collection count:", store.count())


if __name__ == "__main__":
    main()
