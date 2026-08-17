from __future__ import annotations

import re

from langchain_core.documents import Document

from app.services.document.models import ChunkMetadata, DocumentMetadata

PAGE_TAG_PATTERN = re.compile(
    r"<!--\s*(?:page|PAGE|Page|Trang|trang)\s*:?\s*(\d+)\s*-->"
)
HEADER_KEYS_BY_LEVEL = (
    (1, ("h1", "Header 1")),
    (2, ("h2", "Header 2")),
    (3, ("h3", "Header 3")),
    (4, ("h4", "Header 4")),
)
MARKDOWN_HEADING_PATTERN = re.compile(r"^(#{1,4})\s+(.+?)\s*$", re.MULTILINE)


def build_markdown_outline(markdown: str) -> list[dict[str, str | int]]:
    return [
        {
            "text": match.group(2).strip(),
            "level": len(match.group(1)),
            "anchor": f"section-{index}",
        }
        for index, match in enumerate(MARKDOWN_HEADING_PATTERN.finditer(markdown), start=1)
    ]


class MetadataBuilder:
    def build(
        self,
        chunks: list[Document],
        total_pages: int,
        markdown: str | None = None,
    ) -> tuple[DocumentMetadata, list[ChunkMetadata]]:
        total_chunks = len(chunks)
        total_characters = sum(len(c.page_content) for c in chunks)
        total_estimated_tokens = sum(max(1, len(c.page_content) // 4) for c in chunks)

        outline: list[dict[str, str | int]] = []
        previous_header_entries: list[tuple[int, str]] = []
        chunk_metadata_list: list[ChunkMetadata] = []
        current_page_tracker = 1

        for i, chunk in enumerate(chunks):
            content = chunk.page_content
            char_count = len(content)

            header_entries = [
                (level, chunk.metadata[key])
                for level, keys in HEADER_KEYS_BY_LEVEL
                for key in keys
                if key in chunk.metadata
            ]
            header_path = [heading for _, heading in header_entries]
            shared_depth = 0
            while (
                shared_depth < len(previous_header_entries)
                and shared_depth < len(header_entries)
                and previous_header_entries[shared_depth] == header_entries[shared_depth]
            ):
                shared_depth += 1
            for level, heading in header_entries[shared_depth:]:
                outline.append(
                    {
                        "text": heading,
                        "level": level,
                        "anchor": f"section-{len(outline) + 1}",
                    }
                )
            previous_header_entries = header_entries

            found_pages = [int(p) for p in PAGE_TAG_PATTERN.findall(content)]
            page_start = found_pages[0] if found_pages else current_page_tracker
            current_page_tracker = (
                found_pages[-1] if found_pages else current_page_tracker
            )

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
                outline=build_markdown_outline(markdown) if markdown is not None else outline,
            ),
            chunk_metadata_list,
        )
