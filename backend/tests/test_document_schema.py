from pydantic import ValidationError
import pytest

from app.schemas.document_schema import DocumentOut, PastedTextDocumentCreate


def test_document_out_preserves_file_size():
    document = DocumentOut(
        id=1,
        title="lecture.pdf",
        status="completed",
        file_type="pdf",
        file_size=1536,
    )

    assert document.model_dump()["file_size"] == 1536


def test_pasted_text_document_strips_title_and_preserves_content():
    payload = PastedTextDocumentCreate(title="  Lecture notes  ", content="Line 1\nLine 2")

    assert payload.title == "Lecture notes"
    assert payload.content == "Line 1\nLine 2"


@pytest.mark.parametrize(
    ("title", "content"),
    [("", "content"), ("   ", "content"), ("Title", ""), ("Title", "   ")],
)
def test_pasted_text_document_rejects_blank_fields(title: str, content: str):
    with pytest.raises(ValidationError):
        PastedTextDocumentCreate(title=title, content=content)
