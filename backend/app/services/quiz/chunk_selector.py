from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
import re
from typing import Any

from chromadb.api import ClientAPI

from app.services.document.embedding_service import EmbeddingService


@dataclass
class QuizChunk:
    chunk_id: str
    content: str
    metadata: dict[str, Any]


class QuizChunkSelector:
    """
    Select chunks for quiz generation.

    Strategy:

    - With query:
        1. Semantic retrieve
        2. Low-value filtering
        3. Duplicate removal
        4. Context budget fitting

    - Without query:
        1. Retrieve all chunks from active documents.
        2. Remove low-value document metadata sections and non-learning content.
        3. Remove duplicate chunks.
        4. Score structural importance dynamically.
        5. Apply document and section diversity sampling.
        6. Stop based on dynamic context budget.

    The selector does NOT generate questions.
    It only prepares high-quality source context.
    """

    LOW_VALUE_HEADERS = {
        "references",
        "bibliography",
        "acknowledgement",
        "acknowledgements",
        "table of contents",
        "contents",
        "copyright",
        "index",
        "glossary",
        "revision history",
        "license",
        "publication history",
    }

    LOW_VALUE_PATTERNS = [
        r"isbn[-:\s]*[0-9x\-]+",
        r"all rights reserved",
        r"published by",
        r"printed in",
        r"copyright\s*©",
        r"author list",
        r"table of contents",
        r"revision history",
    ]

    MAX_DOCUMENT_RATIO = 0.5

    def __init__(
        self,
        chroma_client: ClientAPI,
        collection_name: str,
        embedding_service: EmbeddingService,
    ):
        self.embedding_service = embedding_service
        self.collection = chroma_client.get_or_create_collection(
            name=collection_name
        )

    async def select(
        self,
        document_ids: list[int],
        total_questions: int,
        coverage: float,
        query: str | None = None,
        reasoning_depth: float = 1.0,
    ) -> list[QuizChunk]:

        context_budget = self._calculate_context_budget(
            total_questions=total_questions,
            coverage=coverage,
            reasoning_depth=reasoning_depth,
        )

        if query:
            candidates = await asyncio.to_thread(
                self._semantic_retrieve,
                document_ids,
                query,
                total_questions,
            )
            candidates = self._filter_low_value_chunks(candidates)
            candidates = self._remove_duplicate_chunks(candidates)
        else:
            candidates = self._coverage_retrieve(
                document_ids=document_ids,
            )
            candidates = self._filter_low_value_chunks(candidates)
            candidates = self._remove_duplicate_chunks(candidates)
            candidates = self._calculate_learning_scores(candidates)
            candidates = self._apply_diversity(candidates)

        return self._fit_context_budget(
            candidates=candidates,
            max_tokens=context_budget,
        )

    # ============================
    # Retrieval
    # ============================

    def _semantic_retrieve(
        self,
        document_ids: list[int],
        query: str,
        total_questions: int,
    ) -> list[dict]:
        where_clause: dict[str, Any]
        if len(document_ids) == 1:
            where_clause = {"document_id": document_ids[0]}
        else:
            where_clause = {"document_id": {"$in": document_ids}}

        n_results = min(
            max(total_questions * 6, 60),
            300,
        )

        query_embedding = self.embedding_service.generate_query_embedding(query)
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause,
        )

        return self._convert_chroma_result(result)

    def _coverage_retrieve(
        self,
        document_ids: list[int],
    ) -> list[dict]:
        where_clause: dict[str, Any]
        if len(document_ids) == 1:
            where_clause = {"document_id": document_ids[0]}
        else:
            where_clause = {"document_id": {"$in": document_ids}}

        result = self.collection.get(
            where=where_clause,
        )

        return self._convert_chroma_result(result)

    # ============================
    # Filtering & Deduplication
    # ============================

    def _filter_low_value_chunks(
        self,
        chunks: list[dict],
    ) -> list[dict]:

        filtered = []

        for chunk in chunks:
            content = chunk.get("content", "").strip()
            content_lower = content.lower()
            words = content.split()

            # Ignore empty or extremely short chunks
            if len(content) < 30 or len(words) < 5:
                continue

            metadata = chunk.get("metadata", {})
            headers = metadata.get("header_path") or []
            if isinstance(headers, str):
                headers = [headers]

            normalized_headers = [str(h).strip().lower() for h in headers if h]

            # Header-based filtering
            is_low_value_header = False
            for h in normalized_headers:
                if any(lvh in h for lvh in self.LOW_VALUE_HEADERS):
                    # Do not discard appendix unless it only contains metadata indicators
                    if "appendix" in h:
                        if any(
                            meta_kw in content_lower
                            for meta_kw in ["isbn", "copyright", "publisher", "license"]
                        ):
                            is_low_value_header = True
                            break
                    else:
                        is_low_value_header = True
                        break

            if is_low_value_header:
                continue

            # Heuristic pattern checks
            pattern_hits = sum(
                1 for pattern in self.LOW_VALUE_PATTERNS if re.search(pattern, content_lower)
            )

            # Discard if high metadata pattern density
            if pattern_hits >= 2 or (pattern_hits >= 1 and len(words) < 60):
                continue

            chunk["metadata_penalty"] = pattern_hits * 2.0
            filtered.append(chunk)

        return filtered

    def _remove_duplicate_chunks(
        self,
        chunks: list[dict],
    ) -> list[dict]:

        seen = set()
        unique_chunks = []

        for chunk in chunks:
            content = chunk.get("content", "")
            normalized = re.sub(r"\s+", " ", content.lower().strip())
            if normalized not in seen:
                seen.add(normalized)
                unique_chunks.append(chunk)

        return unique_chunks

    # ============================
    # Scoring
    # ============================

    def _compute_structural_score(
        self,
        chunk: dict,
    ) -> float:

        metadata = chunk.get("metadata", {})
        content = chunk.get("content", "")
        words = content.split()
        word_count = len(words)

        score = 0.0

        # Header depth (+1.5 per level)
        header_path = metadata.get("header_path") or []
        if isinstance(header_path, str):
            header_path = [header_path]
        score += len(header_path) * 1.5

        # Page span > 1 (+2)
        page_start = metadata.get("page_start")
        page_end = metadata.get("page_end")
        if (
            page_start is not None
            and page_end is not None
            and page_start != page_end
        ):
            score += 2.0

        # Word count / Chunk length
        if 80 <= word_count <= 350:
            score += 3.0
        elif 350 < word_count <= 700:
            score += 1.0
        elif word_count < 50:
            score -= 2.0

        # Chunk level metadata
        chunk_level = metadata.get("chunk_level")
        if chunk_level:
            level_str = str(chunk_level).lower()
            if "intro" in level_str:
                score += 1.0
            elif "subsection" in level_str:
                score += 3.0
            elif "section" in level_str:
                score += 2.0

        return score

    def _calculate_learning_scores(
        self,
        chunks: list[dict],
    ) -> list[dict]:

        for chunk in chunks:
            structural_score = self._compute_structural_score(chunk)
            penalty = chunk.get("metadata_penalty", 0.0)
            chunk["learning_score"] = structural_score - penalty

        return sorted(
            chunks,
            key=lambda x: x.get("learning_score", 0.0),
            reverse=True,
        )

    # ============================
    # Diversity
    # ============================

    def _apply_diversity(
        self,
        chunks: list[dict],
    ) -> list[dict]:

        # Step 1: Group chunks by document_id and major section
        doc_groups = defaultdict(lambda: defaultdict(list))

        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            doc_id = metadata.get("document_id")
            header_path = metadata.get("header_path") or []
            if isinstance(header_path, str):
                header_path = [header_path]

            major_section = str(header_path[0]).strip() if header_path else "__root__"
            doc_groups[doc_id][major_section].append(chunk)

        # Step 2 & 3: For each doc, sort each section by score desc & round-robin across sections
        doc_interleaved = defaultdict(list)

        for doc_id, section_dict in doc_groups.items():
            for section_chunks in section_dict.values():
                section_chunks.sort(
                    key=lambda x: x.get("learning_score", 0.0),
                    reverse=True,
                )

            section_lists = list(section_dict.values())
            remaining = True
            while remaining:
                remaining = False
                for sec_list in section_lists:
                    if sec_list:
                        doc_interleaved[doc_id].append(sec_list.pop(0))
                        remaining = True

        # Step 4: Round-robin across documents
        result = []
        doc_lists = list(doc_interleaved.values())
        remaining = True
        while remaining:
            remaining = False
            for doc_list in doc_lists:
                if doc_list:
                    result.append(doc_list.pop(0))
                    remaining = True

        return result

    # ============================
    # Context Budget & Ratio Balancing
    # ============================

    def _calculate_context_budget(
        self,
        total_questions: int,
        coverage: float,
        reasoning_depth: float = 1.0,
    ) -> int:

        budget = (
            5000
            + int((total_questions ** 0.5) * 1500)
            + int(reasoning_depth * 300)
        )

        multiplier = 0.8 + (coverage / 10.0) * 0.4
        budget = int(budget * multiplier)

        return min(
            max(budget, 5000),
            25000,
        )

    def _fit_context_budget(
        self,
        candidates: list[dict],
        max_tokens: int,
    ) -> list[QuizChunk]:

        selected: list[QuizChunk] = []
        current_tokens = 0
        doc_tokens: dict[Any, int] = defaultdict(int)

        unique_docs = {
            c.get("metadata", {}).get("document_id")
            for c in candidates
            if c.get("metadata", {}).get("document_id") is not None
        }

        per_doc_limit = (
            int(max_tokens * self.MAX_DOCUMENT_RATIO)
            if len(unique_docs) > 1
            else max_tokens
        )

        deferred_candidates = []

        # Pass 1: Select chunks while respecting MAX_DOCUMENT_RATIO
        for chunk in candidates:
            doc_id = chunk.get("metadata", {}).get("document_id")
            tokens = self._estimate_tokens(chunk.get("content", ""))

            if current_tokens + tokens > max_tokens:
                continue

            if len(unique_docs) > 1 and doc_tokens[doc_id] + tokens > per_doc_limit:
                deferred_candidates.append(chunk)
                continue

            selected.append(
                QuizChunk(
                    chunk_id=str(chunk["id"]),
                    content=chunk["content"],
                    metadata=chunk.get("metadata", {}),
                )
            )
            current_tokens += tokens
            doc_tokens[doc_id] += tokens

        # Pass 2: Fill remaining budget with deferred candidates
        for chunk in deferred_candidates:
            tokens = self._estimate_tokens(chunk.get("content", ""))
            if current_tokens + tokens > max_tokens:
                continue

            selected.append(
                QuizChunk(
                    chunk_id=str(chunk["id"]),
                    content=chunk["content"],
                    metadata=chunk.get("metadata", {}),
                )
            )
            current_tokens += tokens

        return selected

    # ============================
    # Utils
    # ============================

    def _convert_chroma_result(
        self,
        result: dict,
    ) -> list[dict]:

        documents = result.get("documents") or []
        ids = result.get("ids") or []
        metadatas = result.get("metadatas") or []

        if documents and isinstance(documents[0], list):
            documents = documents[0]
            ids = ids[0] if ids else []
            metadatas = metadatas[0] if metadatas else []

        output = []
        for idx, content in enumerate(documents):
            metadata = metadatas[idx] if idx < len(metadatas) and metadatas[idx] else {}
            chunk_id = ids[idx] if idx < len(ids) else str(idx)

            output.append(
                {
                    "id": chunk_id,
                    "content": content,
                    "metadata": metadata,
                }
            )

        return output

    def _estimate_tokens(
        self,
        text: str,
    ) -> int:

        return max(
            int(len(text.split()) * 1.3),
            1,
        )
