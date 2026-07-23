from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingClient(ABC):
    """
    Interface chuẩn cho tất cả các Embedding Models (Voyage, OpenAI, Cohere, v.v.)
    """

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Tạo vector embeddings cho danh sách tài liệu/chunks.
        """
        pass

    @abstractmethod
    def embed_query(self, query_text: str) -> List[float]:
        """
        Tạo vector embedding cho 1 câu truy vấn tìm kiếm (Query).
        """
        pass
