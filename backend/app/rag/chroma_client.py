import json
from chromadb import HttpClient
from typing import List, Dict, Any, Optional


def _sanitize_metadata(md: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chroma metadata values must be: str, int, float, bool or None.
    Convert lists/dicts to JSON strings. Convert other unknown types to str.
    """
    clean: Dict[str, Any] = {}
    for k, v in (md or {}).items():
        if v is None:
            clean[k] = None
        elif isinstance(v, (str, int, float, bool)):
            clean[k] = v
        elif isinstance(v, (list, dict)):
            clean[k] = json.dumps(v, ensure_ascii=False)
        else:
            clean[k] = str(v)
    return clean


class ChromaPlaybookStore:
    def __init__(self, host: str, port: int, collection_name: str):
        self.collection_name = collection_name
        self.client = HttpClient(host=host, port=port)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def reset(self):
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
        )

    def count(self) -> int:
        return int(self.collection.count())

    def add_document(
        self,
        *,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        md = dict(metadata or {})

        # ✅ extra: contexts_csv para filtros simples/debug
        if "contexts" in md and isinstance(md["contexts"], list):
            md["contexts_csv"] = ",".join([str(x) for x in md["contexts"]])

        md = _sanitize_metadata(md)

        self.collection.add(
            ids=[str(doc_id)],
            documents=[text],
            metadatas=[md],
        )

    from typing import List, Optional

    def query(
        self, query_text: str, age: Optional[int] = None, n_results: int = 5
    ) -> List[str]:
        """
        Query a Chroma.
        - Soporta age=None (sin filtro).
        - Filtro por edad usa $and (Chroma 1.3.x requiere un solo operador raíz).
        - Devuelve SOLO documents (List[str]).
        """

        where = None
        if age is not None:
            where = {
                "$and": [
                    {"age_min": {"$lte": int(age)}},
                    {"age_max": {"$gte": int(age)}},
                ]
            }

        print(
            "DEBUG CHROMA QUERY:",
            {
                "collection": self.collection_name,
                "n_results": n_results,
                "age": age,
                "query_preview": (query_text or "")[:120],
                "where": where,
            },
        )

        # include: ids no se piden; documents/metadatas son suficientes y estables
        if where is not None:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas"],
            )
        else:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                include=["documents", "metadatas"],
            )

        print(
            "DEBUG CHROMA RAW:",
            type(results),
            results.keys() if hasattr(results, "keys") else None,
        )

        documents: List[str] = (results.get("documents") or [[]])[0] or []
        metadatas = results.get("metadatas") or []
        print(
            "DEBUG CHROMA PROCESSED:",
            {
                "documents_count": len(documents),
                "metadatas_count": len(metadatas),
                "sample_metadata": metadatas[0] if metadatas else None,
            },
        )
        return {
            "documents": documents,
            "metadatas": metadatas,
        }


_CONTEXT_NORMALIZE = {
    "otro contexto social": "otro_contexto_social",
    "otro_contexto_social": "otro_contexto_social",
    "en todas las anteriores": None,  # significa "cualquiera"
}


def _normalize_ctx_token(s: str) -> str:
    s = (s or "").strip().lower()
    return _CONTEXT_NORMALIZE.get(s, s)
