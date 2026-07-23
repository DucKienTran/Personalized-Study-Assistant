import logging
import time
from typing import List

import voyageai

from app.ai.embeddings.base import BaseEmbeddingClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class VoyageEmbeddingClient(BaseEmbeddingClient):
    def __init__(self):
        self.client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        self.model = settings.VOYAGE_MODEL
        self.batch_size = settings.VOYAGE_EMBEDDING_BATCH_SIZE

    def _call_api_with_retry(
        self, texts: List[str], input_type: str, max_retries: int = 5
    ) -> List[List[float]]:
        """
        Gửi request với Exponential Backoff tự động khi dính Rate Limit (429) hoặc lỗi mạng.
        """
        retry_count = 0
        backoff_time = 1.0

        while True:
            try:
                response = self.client.embed(
                    texts=texts, model=self.model, input_type=input_type
                )
                return response.embeddings
            except Exception as e:
                err_msg = str(e).lower()
                is_transient_error = any(
                    kw in err_msg
                    for kw in [
                        "ratelimit",
                        "429",
                        "rate limit",
                        "connection",
                        "timeout",
                        "500",
                        "503",
                    ]
                )

                if is_transient_error:
                    retry_count += 1
                    if retry_count > max_retries:
                        logger.error(
                            f"[Voyage API] Vẫn thất bại sau {max_retries} lần retry. Lỗi: {e}"
                        )
                        raise e

                    logger.warning(
                        f"[Voyage API] Lỗi tạm thời ({e}). Thử lại lần {retry_count}/{max_retries} sau {backoff_time}s..."
                    )
                    time.sleep(backoff_time)
                    backoff_time *= 2.0
                else:
                    raise e

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        all_embeddings = []
        total_texts = len(texts)
        total_batches = (total_texts + self.batch_size - 1) // self.batch_size

        logger.info(
            f"[VoyageClient] Đang embed {total_texts} chunks qua {total_batches} batch(es)..."
        )

        for i in range(0, total_texts, self.batch_size):
            batch_texts = texts[i : i + self.batch_size]
            current_batch_num = (i // self.batch_size) + 1

            logger.info(
                f"[VoyageClient] Gửi Batch {current_batch_num}/{total_batches} ({len(batch_texts)} items)..."
            )

            embeddings = self._call_api_with_retry(batch_texts, input_type="document")
            all_embeddings.extend(embeddings)

        return all_embeddings

    def embed_query(self, query_text: str) -> List[float]:
        return self._call_api_with_retry([query_text], input_type="query")[0]
