from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


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
        chunk_size: int = 450,
        chunk_overlap: int = 0,
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

        return final_chunks
