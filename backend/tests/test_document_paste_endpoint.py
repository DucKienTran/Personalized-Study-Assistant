from types import SimpleNamespace

from fastapi import BackgroundTasks
import pytest

from app.api.documents import create_document_from_text
from app.schemas.document_schema import PastedTextDocumentCreate


class FakeDocumentService:
    def __init__(self):
        self.upload_args = None

    async def upload_and_init_document(self, **kwargs):
        self.upload_args = kwargs
        return SimpleNamespace(
            id=7,
            title=kwargs["title"],
            status="pending",
            file_type="txt",
            file_size=len(kwargs["file_bytes"]),
            created_at=None,
            mongo_id="mongo-7",
            file_path="object.txt",
        )


class FakeProcessingService:
    async def execute_processing_pipeline(self, **_kwargs):
        return None


@pytest.mark.asyncio
async def test_paste_text_endpoint_stores_txt_and_schedules_existing_pipeline():
    background_tasks = BackgroundTasks()
    document_service = FakeDocumentService()
    processing_service = FakeProcessingService()

    response = await create_document_from_text(
        payload=PastedTextDocumentCreate(title="Study notes", content="Nội dung"),
        background_tasks=background_tasks,
        doc_service=document_service,
        processing_service=processing_service,
        current_user=SimpleNamespace(id=3),
    )

    assert response.data.id == 7
    assert document_service.upload_args == {
        "file_bytes": "Nội dung".encode("utf-8"),
        "filename": "pasted-text.txt",
        "user_id": 3,
        "title": "Study notes",
    }
    assert len(background_tasks.tasks) == 1
    assert background_tasks.tasks[0].func == processing_service.execute_processing_pipeline
    assert background_tasks.tasks[0].kwargs == {
        "document_id": 7,
        "mongo_id": "mongo-7",
        "object_name": "object.txt",
    }
