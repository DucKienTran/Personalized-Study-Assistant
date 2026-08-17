from __future__ import annotations

from typing import Iterable

import tiktoken

from app.services.summary.models import DigestSource


class TokenBatcher:
    """
    Greedy sequential batching.
    Đảm bảo:

    total_tokens(batch)
        <= max_tokens
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        max_tokens: int = 12000,
    ):
        self.encoder = tiktoken.encoding_for_model(model)
        self.max_tokens = max_tokens

    def _count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))

    def build(
        self,
        units: Iterable[DigestSource],
    ) -> list[list[DigestSource]]:
        batches: list[list[DigestSource]] = []

        current_batch: list[DigestSource] = []
        current_tokens = 0

        for unit in units:

            token_count = self._count_tokens(unit.content)

            if current_batch and current_tokens + token_count > self.max_tokens:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0

            current_batch.append(unit)
            current_tokens += token_count

        if current_batch:
            batches.append(current_batch)

        return batches
