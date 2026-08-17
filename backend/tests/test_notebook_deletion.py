from types import SimpleNamespace

from bson import ObjectId
from pymongo.errors import PyMongoError
import pytest

from app.services.notebook.notebook_service import NotebookService


class FakeDb:
    def __init__(self):
        self.deleted = []
        self.flushed = False
        self.committed = False
        self.rolled_back = False

    def delete(self, value):
        self.deleted.append(value)

    def flush(self):
        self.flushed = True

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class FakeSummaryCollection:
    def __init__(self, error=None):
        self.query = None
        self.error = error

    async def delete_many(self, query):
        if self.error:
            raise self.error
        self.query = query


class FakeMongoDb:
    def __init__(self, collection):
        self.collection = collection

    def __getitem__(self, name):
        assert name == "notebook_summaries"
        return self.collection


@pytest.mark.asyncio
async def test_delete_notebook_removes_summaries_but_not_documents():
    summary_id = ObjectId()
    document = SimpleNamespace(id=9)
    notebook = SimpleNamespace(
        id=1,
        summaries=[SimpleNamespace(mongo_summary_id=str(summary_id))],
        notebook_documents=[SimpleNamespace(document=document)],
    )
    db = FakeDb()
    collection = FakeSummaryCollection()
    service = NotebookService(db)
    service._get_owned_notebook = lambda _notebook_id, _user_id: notebook

    result = await service.delete_notebook(
        notebook_id=1,
        current_user=SimpleNamespace(id=2),
        mongo_db=FakeMongoDb(collection),
    )

    assert result == {"detail": "Notebook deleted successfully."}
    assert db.deleted == [notebook]
    assert document not in db.deleted
    assert db.flushed is True
    assert db.committed is True
    assert collection.query == {"_id": {"$in": [summary_id]}}


@pytest.mark.asyncio
async def test_delete_notebook_rolls_back_when_summary_cleanup_fails():
    notebook = SimpleNamespace(
        id=1,
        summaries=[SimpleNamespace(mongo_summary_id=str(ObjectId()))],
    )
    db = FakeDb()
    service = NotebookService(db)
    service._get_owned_notebook = lambda _notebook_id, _user_id: notebook

    with pytest.raises(Exception) as exc_info:
        await service.delete_notebook(
            notebook_id=1,
            current_user=SimpleNamespace(id=2),
            mongo_db=FakeMongoDb(FakeSummaryCollection(PyMongoError("unavailable"))),
        )

    assert getattr(exc_info.value, "status_code", None) == 500
    assert db.rolled_back is True
    assert db.committed is False
