import logging

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 0


class DocumentChunkBuilder:
    """
    Chunk markdown documents using LangChain.

    Pipeline

    Markdown
        ↓
    MarkdownHeaderTextSplitter
        ↓
    RecursiveCharacterTextSplitter (optional)
        ↓
    List[Document]
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> None:

        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "h1"),
                ("##", "h2"),
                ("###", "h3"),
                ("####", "h4"),
            ],
            strip_headers=False,
        )

        self.recursive_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def build(
        self,
        markdown: str,
    ) -> list[Document]:
        """
        Convert markdown into final chunks.
        """

        sections = self.header_splitter.split_text(markdown)
        final_chunks: list[Document] = []

        for section in sections:
            chunks = self.recursive_splitter.split_documents([section])
            final_chunks.extend(chunks)
        logger.info(f"Header sections={len(sections)}")
        logger.info(f"Final chunks={len(final_chunks)}")
        return final_chunks
