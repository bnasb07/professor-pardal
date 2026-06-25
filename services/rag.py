import asyncio
from pathlib import Path
from typing import List, Dict

from services.document_parser import DocumentParser


class RAGService:
    def __init__(self, materials_dir: Path, db_dir: Path = None):
        self.materials_dir = materials_dir
        self.db_dir = db_dir if db_dir is not None else (materials_dir.parent / ".pardal_db")
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.parser = DocumentParser()
        self._model = None
        self._client = None
        self._collection = None
        self._indexed_files: set = set()
        self._indexing: set = set()

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        return self._model

    def _get_collection(self):
        if self._collection is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=str(self.db_dir))
            self._collection = self._client.get_or_create_collection(
                name="study_materials",
                metadata={"hnsw:space": "cosine"}
            )
            self._load_indexed_files()
        return self._collection

    def _load_indexed_files(self):
        try:
            results = self._collection.get(include=["metadatas"])
            for meta in results.get("metadatas", []):
                if meta and "source" in meta:
                    self._indexed_files.add(meta["source"])
        except Exception:
            pass

    def is_indexed(self, filename: str) -> bool:
        return filename in self._indexed_files

    def is_indexing(self, filename: str) -> bool:
        return filename in self._indexing

    async def index_document(self, path: Path):
        if path.name in self._indexing:
            return
        self._indexing.add(path.name)
        try:
            await self._do_index(path)
        finally:
            self._indexing.discard(path.name)

    async def _do_index(self, path: Path):
        loop = asyncio.get_running_loop()

        chunks = await loop.run_in_executor(None, self.parser.parse, path)
        if not chunks:
            print(f"Nenhum chunk extraído de {path.name}")
            return

        texts = [c["text"] for c in chunks]
        model = self._get_model()
        embeddings = await loop.run_in_executor(
            None, lambda: model.encode(texts, show_progress_bar=False).tolist()
        )

        collection = self._get_collection()

        ids = [
            f"{path.name}__p{c['page']}__par{c['paragraph']}__{i}"
            for i, c in enumerate(chunks)
        ]
        metadatas = [
            {
                "source": path.name,
                "page": str(c["page"]),
                "paragraph": str(c["paragraph"]),
            }
            for c in chunks
        ]

        self.remove_document(path.name)  # safe: replaces in full before adding new

        batch_size = 100
        for i in range(0, len(texts), batch_size):
            collection.add(
                ids=ids[i:i + batch_size],
                embeddings=embeddings[i:i + batch_size],
                documents=texts[i:i + batch_size],
                metadatas=metadatas[i:i + batch_size],
            )

        self._indexed_files.add(path.name)
        print(f"Indexado: {path.name} ({len(chunks)} chunks)")

    def remove_document(self, filename: str):
        try:
            collection = self._get_collection()
            results = collection.get(where={"source": filename}, include=["ids"])
            if results and results.get("ids"):
                collection.delete(ids=results["ids"])
        except Exception:
            pass
        self._indexed_files.discard(filename)

    async def search(self, query: str, top_k: int = 6) -> List[Dict]:
        loop = asyncio.get_running_loop()
        collection = self._get_collection()

        count = collection.count()
        if count == 0:
            return []

        model = self._get_model()
        embedding = await loop.run_in_executor(
            None, lambda: model.encode([query], show_progress_bar=False).tolist()
        )

        n = min(top_k, count)
        results = collection.query(
            query_embeddings=embedding,
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )

        output = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            if dist < 0.85:
                output.append({
                    "text": doc,
                    "source": meta.get("source", ""),
                    "page": meta.get("page", "?"),
                    "paragraph": meta.get("paragraph", "?"),
                    "relevance": round(1 - dist, 3),
                })

        return sorted(output, key=lambda x: x["relevance"], reverse=True)
