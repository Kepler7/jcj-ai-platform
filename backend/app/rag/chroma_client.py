from chromadb import HttpClient
from typing import List, Dict

class ChromaPlaybookStore:
    def __init__(self, host: str, port: int, collection_name: str):
        self.client = HttpClient(host=host, port=port)
        self.collection = self.client.get_or_create_collection(
            name=collection_name
        )

    def add_playbook(
        self,
        playbook_id: str,
        content: str,
        metadata: Dict
    ):
        self.collection.add(
            ids=[playbook_id],
            documents=[content],
            metadatas=[metadata],
        )

    def query(
        self,
        query_text: str,
        age: int,
        context: str,
        n_results: int = 5,
    ) -> List[str]:
        """
        Busca playbooks relevantes por similitud semántica, filtrando:
        - En Chroma: solo por edad (porque esta versión no soporta $contains).
        - En Python: filtra por 'context' usando el metadata 'context' guardado como string "aula,casa".
        Devuelve una lista de DOCUMENTOS (strings) ordenados por relevancia.
        """

        # 1) Query vectorial (Chroma) + filtro por edad (operadores soportados)
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where={
                "$and": [
                    {"age_min": {"$lte": age}},
                    {"age_max": {"$gte": age}},
                ]
            },
            include=["documents", "metadatas"],
        )

        # 2) Extrae docs y metadatas (Chroma regresa listas por cada query_text)
        documents: List[str] = results.get("documents", [[]])[0] or []
        metadatas: List[Dict[str, Any]] = results.get("metadatas", [[]])[0] or []

        # 3) Filtra por contexto en Python (porque Chroma no soporta $contains)
        #    Nota: 'context' en metadata es un string "aula,casa"
        context = (context or "").strip().lower()

        if context:
            filtered_docs = []
            for doc, meta in zip(documents, metadatas):
                meta_context = (meta.get("context") or "").lower()
                if context in meta_context:
                    filtered_docs.append(doc)
            return filtered_docs

        # Si no pasas context, devuelve tal cual
        return documents
