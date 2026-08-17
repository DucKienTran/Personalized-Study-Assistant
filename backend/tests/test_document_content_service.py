from types import SimpleNamespace

import pytest

from app.services.document.document_service import DocumentService


class FakeMongoCollection:
    def __init__(self, document: dict):
        self.document = document

    async def find_one(self, _query: dict):
        return self.document


@pytest.mark.asyncio
async def test_document_content_uses_processed_raw_text_and_builds_legacy_outline():
    service = DocumentService.__new__(DocumentService)
    service.mongo_collection = FakeMongoCollection(
        {
            "raw_text": "# First\n\nText\n\n## Child\n\nMore text",
            "outline": ["Child", "First"],
        }
    )
    service._get_owned_document = lambda _document_id, _user_id: SimpleNamespace(
        title="Notes",
        file_type="md",
        mongo_id="legacy-id",
    )

    content = await service.get_document_content(document_id=1, user_id=2)

    assert content["content_raw"].startswith("# First")
    assert content["outline"] == [
        {"text": "First", "level": 1, "anchor": "section-1"},
        {"text": "Child", "level": 2, "anchor": "section-2"},
    ]
