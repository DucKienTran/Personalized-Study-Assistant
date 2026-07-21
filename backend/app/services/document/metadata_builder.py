from __future__ import annotations

import re

from langchain_core.documents import Document

from app.services.document.models import ChunkMetadata, DocumentMetadata

PAGE_TAG_PATTERN = re.compile(r"<!--\s*(?:page|PAGE|Page|Trang|trang)\s*:?\s*(\d+)\s*-->")
HEADER_KEYS = ("h1", "h2", "h3", "h4", "Header 1", "Header 2", "Header 3", "Header 4")


class MetadataBuilder:
    def build(
        self,
        chunks: list[Document],
        total_pages: int,
    ) -> tuple[DocumentMetadata, list[ChunkMetadata]]:
        total_chunks = len(chunks)
        total_characters = sum(len(c.page_content) for c in chunks)
        total_estimated_tokens = sum(max(1, len(c.page_content) // 4) for c in chunks)

        headings: set[str] = set()
        chunk_metadata_list: list[ChunkMetadata] = []
        current_page_tracker = 1

        for i, chunk in enumerate(chunks):
            content = chunk.page_content
            char_count = len(content)

            header_path = [chunk.metadata[k] for k in HEADER_KEYS if k in chunk.metadata]
            headings.update(header_path)

            found_pages = [int(p) for p in PAGE_TAG_PATTERN.findall(content)]
            page_start = found_pages[0] if found_pages else current_page_tracker
            current_page_tracker = found_pages[-1] if found_pages else current_page_tracker

            chunk_metadata_list.append(
                ChunkMetadata(
                    chunk_id=f"chunk_{i + 1}",
                    header_path=header_path,
                    page_start=page_start,
                    page_end=current_page_tracker,
                    estimated_tokens=max(1, char_count // 4),
                    character_count=char_count,
                    previous_chunk=f"chunk_{i}" if i > 0 else None,
                    next_chunk=f"chunk_{i + 2}" if i < total_chunks - 1 else None,
                )
            )

        return (
            DocumentMetadata(
                total_pages=total_pages,
                total_chunks=total_chunks,
                total_characters=total_characters,
                estimated_tokens=total_estimated_tokens,
                headings=sorted(headings),
            ),
            chunk_metadata_list,
        )
