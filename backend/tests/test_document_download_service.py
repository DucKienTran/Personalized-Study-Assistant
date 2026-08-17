from types import SimpleNamespace

import pytest

from app.services.document.document_service import DocumentService


class FakeStorage:
    def __init__(self):
        self.calls = []

    async def get_presigned_url(self, **kwargs):
        self.calls.append(kwargs)
        return "https://storage.example/download"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("title", "file_type", "expected_filename", "expected_content_type"),
    [
        ("guide.pdf", "pdf", "guide.pdf", "application/pdf"),
        (
            "notes",
            "docx",
            "notes.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        ("chapter.md (1)", "md", "chapter (1).md", "text/markdown; charset=utf-8"),
        ("lecture", "txt", "lecture.txt", "text/plain; charset=utf-8"),
    ],
)
async def test_download_url_uses_attachment_headers(
    title,
    file_type,
    expected_filename,
    expected_content_type,
):
    service = object.__new__(DocumentService)
    service.storage_service = FakeStorage()
    service._get_owned_document = lambda document_id, user_id: SimpleNamespace(
        title=title,
        file_type=file_type,
        file_path="stored-object",
    )

    url = await service.get_document_download_url(document_id=7, user_id=3)

    assert url == "https://storage.example/download"
    call = service.storage_service.calls[0]
    assert call["object_name"] == "stored-object"
    assert f'filename="{expected_filename}"' in call["response_headers"]["response-content-disposition"]
    assert call["response_headers"]["response-content-type"] == expected_content_type


@pytest.mark.asyncio
async def test_download_url_rejects_non_owned_document():
    service = object.__new__(DocumentService)
    service.storage_service = FakeStorage()
    service._get_owned_document = lambda document_id, user_id: None

    assert await service.get_document_download_url(document_id=7, user_id=3) is None
    assert service.storage_service.calls == []
