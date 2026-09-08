from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bson import ObjectId
import pytest

from app.models.notebook_model import Notebook, NotebookSummary
from app.services.summary.summary_service import (
    GeneratedNotebookSummary,
    SummaryService,
    _derive_summary_title,
)


class FakeQuery:
    def __init__(self, model, notebook, summaries):
        self.model = model
        self.notebook = notebook
        self.summaries = summaries

    def filter(self, *args):
        return self

    def first(self):
        return self.notebook if self.model is Notebook else None

    def all(self):
        return list(self.summaries) if self.model is NotebookSummary else []


class FakeSession:
    def __init__(self, notebook):
        self.notebook = notebook
        self.summaries = []

    def query(self, model):
        return FakeQuery(model, self.notebook, self.summaries)

    def add(self, record):
        record.id = len(self.summaries) + 1
        record.created_at = datetime.now(UTC)
        self.summaries.append(record)

    def commit(self):
        pass

    def refresh(self, record):
        pass


class FakeCollection:
    def __init__(self):
        self.documents = {}
        self.insert_count = 0

    async def insert_one(self, document):
        object_id = ObjectId()
        self.documents[object_id] = document
        self.insert_count += 1
        return SimpleNamespace(inserted_id=object_id)

    async def find_one(self, query):
        return self.documents.get(query["_id"])


class LifecycleSummaryService(SummaryService):
    async def _get_or_generate_document_digest(self, doc):
        return {"title": doc.title, "overview": "Existing digest"}


def test_summary_title_uses_markdown_heading_and_fallback():
    assert _derive_summary_title(
        "# **Java Fundamentals and Object-Oriented Design**\n\nContent",
        "Programming",
    ) == "Java Fundamentals and Object-Oriented Design"
    assert _derive_summary_title("Summary without a heading", "Programming") == (
        "Programming Summary"
    )


@pytest.mark.asyncio
async def test_generation_persists_once_and_cache_reuses_resource():
    document = SimpleNamespace(id=12, title="Java")
    notebook = SimpleNamespace(
        id=9,
        user_id=4,
        title="Programming",
        notebook_documents=[SimpleNamespace(is_active=True, document=document)],
    )
    sql_db = FakeSession(notebook)
    summary_collection = FakeCollection()
    mongo_db = {
        "parsed_documents": FakeCollection(),
        "notebook_summaries": summary_collection,
    }
    llm_client = SimpleNamespace(
        generate=AsyncMock(
            return_value="# Java Fundamentals\n\nGenerated content"
        )
    )
    service = LifecycleSummaryService(sql_db, mongo_db, SimpleNamespace(), llm_client)

    first = await service.generate_notebook_summary(
        user_id=4,
        notebook_id=9,
        level="standard",
        format_type="markdown",
        instruction="",
        include_record=True,
    )
    second = await service.generate_notebook_summary(
        user_id=4,
        notebook_id=9,
        level="standard",
        format_type="markdown",
        instruction="",
        include_record=True,
    )

    assert isinstance(first, GeneratedNotebookSummary)
    assert isinstance(second, GeneratedNotebookSummary)
    assert first.record.id == second.record.id == 1
    assert first.record.title == "Java Fundamentals"
    assert len(sql_db.summaries) == 1
    assert summary_collection.insert_count == 1
    llm_client.generate.assert_awaited_once()
