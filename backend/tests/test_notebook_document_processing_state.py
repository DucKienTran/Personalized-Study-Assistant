from types import SimpleNamespace

from fastapi import HTTPException
import pytest

from app.schemas.notebook_schema import ToggleDocumentActiveRequest
from app.services.notebook.notebook_service import NotebookService


class FakeQuery:
    def __init__(self, mapping):
        self.mapping = mapping

    def filter_by(self, **_kwargs):
        return self

    def first(self):
        return self.mapping


class FakeDb:
    def __init__(self, mapping):
        self.mapping = mapping
        self.deleted = None

    def query(self, _model):
        return FakeQuery(self.mapping)

    def delete(self, value):
        self.deleted = value

    def commit(self):
        return None


def build_service(status: str):
    mapping = SimpleNamespace(
        document_id=3,
        document=SimpleNamespace(status=status, file_size=10),
        is_active=True,
    )
    db = FakeDb(mapping)
    service = NotebookService(db)
    notebook = SimpleNamespace(id=1, user_id=2, notebook_documents=[mapping])
    service._get_owned_notebook = lambda _notebook_id, _user_id: notebook
    user = SimpleNamespace(id=2)
    return service, db, mapping, notebook, user


def test_processing_document_is_not_counted_as_active():
    service, _db, _mapping, notebook, _user = build_service("processing")

    stats = service._calculate_notebook_statistics(
        SimpleNamespace(
            notebook_documents=notebook.notebook_documents,
            quizzes=[],
            conversations=[],
        )
    )

    assert stats["active_document_count"] == 0


def test_processing_document_cannot_be_toggled():
    service, _db, _mapping, _notebook, user = build_service("processing")

    with pytest.raises(HTTPException) as exc_info:
        service.toggle_document_active(
            notebook_id=1,
            document_id=3,
            current_user=user,
            data=ToggleDocumentActiveRequest(is_active=False),
        )

    assert exc_info.value.status_code == 409


def test_processing_document_can_still_be_removed():
    service, db, mapping, _notebook, user = build_service("processing")

    service.remove_document(notebook_id=1, document_id=3, current_user=user)

    assert db.deleted is mapping
