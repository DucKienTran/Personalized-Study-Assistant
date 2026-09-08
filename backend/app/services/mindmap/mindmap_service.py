from __future__ import annotations

import json
import logging
import re
from typing import Any

from chromadb.api import ClientAPI
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.llm.base import LLMClient
from app.ai.prompts.mindmap_prompt import MindmapPromptBuilder, MindmapSource
from app.core.config import settings
from app.models.notebook_model import Mindmap, Notebook
from app.schemas.mindmap_schema import MindmapCreate
from app.schemas.user_schema import CurrentUser
from app.services.mindmap.constants import MAX_CHILDREN_PER_NODE, MAX_DEPTH, MAX_NODES

logger = logging.getLogger(__name__)


class MindmapService:
    MAX_SOURCE_CHARS = 50000
    MAX_CHUNKS = 60

    def __init__(self, db: Session, chroma_client: ClientAPI, llm_client: LLMClient):
        self.db = db
        self.chroma_client = chroma_client
        self.llm_client = llm_client

    def _get_owned_notebook(self, notebook_id: int, user_id: int) -> Notebook:
        notebook = self.db.query(Notebook).filter(Notebook.id == notebook_id).first()
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found.")
        if notebook.user_id != user_id:
            # Deliberately hide resource existence from unauthorized users.
            raise HTTPException(status_code=404, detail="Notebook not found.")
        return notebook

    def _get_owned_mindmap(self, notebook_id: int, mindmap_id: int, user_id: int) -> Mindmap:
        self._get_owned_notebook(notebook_id, user_id)
        mindmap = (
            self.db.query(Mindmap)
            .filter(Mindmap.id == mindmap_id, Mindmap.notebook_id == notebook_id)
            .first()
        )
        if not mindmap:
            raise HTTPException(status_code=404, detail="Mindmap not found.")
        return mindmap

    def list_mindmaps(self, notebook_id: int, current_user: CurrentUser) -> list[Mindmap]:
        self._get_owned_notebook(notebook_id, current_user.id)
        return (
            self.db.query(Mindmap)
            .filter(Mindmap.notebook_id == notebook_id)
            .order_by(Mindmap.created_at.desc())
            .all()
        )

    def get_mindmap(self, notebook_id: int, mindmap_id: int, current_user: CurrentUser) -> Mindmap:
        return self._get_owned_mindmap(notebook_id, mindmap_id, current_user.id)

    async def create_mindmap(
        self,
        notebook_id: int,
        payload: MindmapCreate,
        current_user: CurrentUser,
    ) -> Mindmap:
        notebook = self._get_owned_notebook(notebook_id, current_user.id)
        source_document_ids = [
            nd.document_id
            for nd in notebook.notebook_documents
            if nd.is_active and nd.document and nd.document.status == "completed"
        ]
        if not source_document_ids:
            raise HTTPException(
                status_code=400,
                detail="At least one active, processed document is required to create a mindmap.",
            )

        sources = self._collect_sources(source_document_ids)
        if not sources:
            raise HTTPException(status_code=400, detail="No usable source content was found.")

        prompt = MindmapPromptBuilder.build(
            notebook_title=notebook.title,
            sources=sources,
            max_nodes=MAX_NODES,
            max_depth=MAX_DEPTH,
            max_children_per_node=MAX_CHILDREN_PER_NODE,
        )
        raw = await self.llm_client.generate(prompt=prompt)
        content = self._parse_and_validate(raw)

        title = (payload.title or content.get("label") or notebook.title).strip()[:255]
        mindmap = Mindmap(
            notebook_id=notebook.id,
            title=title,
            content_json=content,
            source_document_ids=source_document_ids,
        )
        try:
            self.db.add(mindmap)
            self.db.commit()
            self.db.refresh(mindmap)
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error("Database error while creating mindmap: %s", exc)
            raise HTTPException(
                status_code=500, detail="An error occurred while creating the mindmap."
            ) from exc
        return mindmap

    def delete_mindmap(
        self,
        notebook_id: int,
        mindmap_id: int,
        current_user: CurrentUser,
    ) -> None:
        mindmap = self._get_owned_mindmap(notebook_id, mindmap_id, current_user.id)
        try:
            self.db.delete(mindmap)
            self.db.commit()
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error("Database error while deleting mindmap: %s", exc)
            raise HTTPException(
                status_code=500, detail="An error occurred while deleting the mindmap."
            ) from exc

    def _collect_sources(self, document_ids: list[int]) -> list[MindmapSource]:
        collection = self.chroma_client.get_collection(settings.CHROMA_COLLECTION_NAME)
        result = collection.get(
            where={"document_id": {"$in": document_ids}},
            include=["documents", "metadatas"],
        )
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []

        grouped: dict[int, list[tuple[str, dict[str, Any]]]] = {doc_id: [] for doc_id in document_ids}
        for text, metadata in zip(documents, metadatas):
            if not text:
                continue
            metadata = metadata or {}
            try:
                doc_id = int(metadata.get("document_id"))
            except (TypeError, ValueError):
                continue
            if doc_id in grouped:
                grouped[doc_id].append((str(text), metadata))

        for chunks in grouped.values():
            chunks.sort(
                key=lambda item: (
                    item[1].get("page_start", 0),
                    item[1].get("page_end", 0),
                    str(item[1].get("chunk_id", "")),
                )
            )

        # Round-robin across documents gives broad coverage instead of over-sampling one long source.
        selected: list[MindmapSource] = []
        total_chars = 0
        round_index = 0
        while len(selected) < self.MAX_CHUNKS and total_chars < self.MAX_SOURCE_CHARS:
            added = False
            for doc_id in document_ids:
                chunks = grouped.get(doc_id) or []
                if round_index >= len(chunks):
                    continue
                text, metadata = chunks[round_index]
                title = metadata.get("document_title") or f"Document {doc_id}"
                chunk_id = str(metadata.get("chunk_id") or f"document-{doc_id}-chunk-{round_index}")
                content = text.strip()
                block = f"Source ID:\n{chunk_id}\n\nDocument ID:\n{doc_id}\n\nDocument:\n{title}\n\nContent:\n{content}"
                separator = "\n\n---\n\n" if selected else ""
                remaining = self.MAX_SOURCE_CHARS - total_chars - len(separator)
                if remaining <= 0:
                    break
                if len(block) > remaining:
                    content = content[: max(0, remaining - (len(block) - len(content)))]
                    block = block[:remaining]
                if not content:
                    continue
                selected.append(
                    MindmapSource(
                        document_id=doc_id,
                        document_title=str(title),
                        chunk_id=chunk_id,
                        content=content,
                    )
                )
                total_chars += len(separator) + len(block)
                added = True
                if len(selected) >= self.MAX_CHUNKS or total_chars >= self.MAX_SOURCE_CHARS:
                    break
            if not added:
                break
            round_index += 1

        return selected

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        text = raw.strip()
        fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL | re.IGNORECASE)
        if fenced:
            text = fenced.group(1)
        else:
            start, end = text.find("{"), text.rfind("}")
            if start >= 0 and end > start:
                text = text[start : end + 1]
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=502, detail="AI returned invalid mindmap JSON.") from exc
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=502, detail="AI returned an invalid mindmap structure.")
        return parsed

    def _parse_and_validate(self, raw: str) -> dict[str, Any]:
        root = self._extract_json(raw)
        seen_ids: set[str] = set()
        node_count = 0

        def validate(node: Any, depth: int) -> dict[str, Any]:
            nonlocal node_count
            if not isinstance(node, dict):
                raise HTTPException(status_code=502, detail="Mindmap node must be an object.")
            if set(node) != {"id", "label", "children"}:
                raise HTTPException(
                    status_code=502,
                    detail="Mindmap nodes must contain only id, label, and children.",
                )
            if depth > MAX_DEPTH:
                raise HTTPException(status_code=502, detail="Generated mindmap is too deep.")
            node_id_value = node.get("id")
            label_value = node.get("label")
            children = node.get("children")
            if (
                not isinstance(node_id_value, str)
                or not isinstance(label_value, str)
                or not isinstance(children, list)
            ):
                raise HTTPException(status_code=502, detail="Generated mindmap has invalid nodes.")
            node_id = node_id_value.strip()
            label = label_value.strip()
            if not node_id or not label:
                raise HTTPException(status_code=502, detail="Generated mindmap has invalid nodes.")
            if node_id in seen_ids:
                raise HTTPException(status_code=502, detail="Generated mindmap contains duplicate node IDs.")
            seen_ids.add(node_id)
            node_count += 1
            if node_count > MAX_NODES:
                raise HTTPException(status_code=502, detail="Generated mindmap has too many nodes.")
            if len(children) > MAX_CHILDREN_PER_NODE:
                raise HTTPException(
                    status_code=502,
                    detail="Generated mindmap has too many children on one node.",
                )
            return {
                "id": node_id,
                "label": label[:160],
                "children": [validate(child, depth + 1) for child in children],
            }

        return validate(root, 1)
