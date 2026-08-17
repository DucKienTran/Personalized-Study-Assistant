from langchain_core.documents import Document

from app.services.document.metadata_builder import MetadataBuilder


def test_outline_preserves_heading_order_levels_and_anchors():
    chunks = [
        Document(page_content="# First", metadata={"h1": "First"}),
        Document(
            page_content="## Child",
            metadata={"h1": "First", "h2": "Child"},
        ),
        Document(page_content="# Second", metadata={"h1": "Second"}),
        Document(page_content="### Deep", metadata={"h3": "Deep"}),
    ]

    metadata, _ = MetadataBuilder().build(chunks, total_pages=1)

    assert metadata.outline == [
        {"text": "First", "level": 1, "anchor": "section-1"},
        {"text": "Child", "level": 2, "anchor": "section-2"},
        {"text": "Second", "level": 1, "anchor": "section-3"},
        {"text": "Deep", "level": 3, "anchor": "section-4"},
    ]


def test_outline_from_parsed_markdown_preserves_duplicate_headings():
    chunks = [Document(page_content="content", metadata={"h1": "Repeated"})]

    metadata, _ = MetadataBuilder().build(
        chunks,
        total_pages=1,
        markdown="# Repeated\n\nText\n\n# Repeated\n\nMore text",
    )

    assert metadata.outline == [
        {"text": "Repeated", "level": 1, "anchor": "section-1"},
        {"text": "Repeated", "level": 1, "anchor": "section-2"},
    ]
