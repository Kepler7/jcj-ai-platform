import yaml
from pathlib import Path
from app.rag.chroma_client import ChromaPlaybookStore

PLAYBOOK_DIR = Path("data/playbooks")

store = ChromaPlaybookStore(
    host="chroma",
    port=8000,
    collection_name="jcj_playbooks_v1",
)

for file in PLAYBOOK_DIR.glob("*.yaml"):
    with open(file, "r") as f:
        pb = yaml.safe_load(f)

    store.add_playbook(
        playbook_id=pb["id"],
        content=pb["content"],
        metadata={
            "age_min": pb["age_min"],
            "age_max": pb["age_max"],
            "topic": pb["topic"],
            "context": ",".join(pb.get("context", [])),
            "title": pb["title"],
        },
    )

    print(f"Loaded {pb['id']}")