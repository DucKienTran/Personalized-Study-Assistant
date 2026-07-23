# app/services/ai/embedding_service.py
from typing import List, Any, Optional
from app.ai.embeddings.base import BaseEmbeddingClient
from app.ai.embeddings.voyage_client import VoyageEmbeddingClient


class EmbeddingService:
    def __init__(self, client: Optional[BaseEmbeddingClient] = None):
        self.client = client or VoyageEmbeddingClient()

    def _build_text_to_embed(self, chunk: Any) -> str:
        """
        Lấy thông tin an toàn cho cả Dict lẫn Class Object
        """
        if isinstance(chunk, dict):
            header_path = chunk.get("header_path", [])
            content = chunk.get("content", "")
        else:
            header_path = getattr(chunk, "header_path", [])
            content = getattr(chunk, "content", "")

        if header_path:
            header_context = " > ".join(header_path)
            return f"Context: {header_context}\n\n{content}"
        return content

    def generate_chunks_embeddings(
        self, chunks: List[Any], chunk_metadata: List[Any]
    ) -> None:
        """
        Tạo vector cho danh sách chunks và gán trực tiếp vào cm.embedding của ChunkMetadata.
        """
        if not chunks or not chunk_metadata:
            return

        texts_to_embed = []
        for chunk, cm in zip(chunks, chunk_metadata):
            header_path = getattr(cm, "header_path", [])
            content = getattr(
                chunk, "page_content", getattr(chunk, "content", str(chunk))
            )

            if header_path:
                header_context = " > ".join(header_path)
                text = f"Context: {header_context}\n\n{content}"
            else:
                text = content

            texts_to_embed.append(text)

        embeddings = self.client.embed_documents(texts_to_embed)
        for cm, emb in zip(chunk_metadata, embeddings):
            cm.embedding = emb

    def generate_query_embedding(self, query: str) -> List[float]:
        return self.client.embed_query(query)
