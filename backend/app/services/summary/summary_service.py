from datetime import UTC, datetime
import json
import logging
import re

from bson import ObjectId
from chromadb.api import ClientAPI
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.llm.base import LLMClient
from app.ai.prompts.summary_prompt import SummaryPromptBuilder
from app.core.config import settings
from app.exceptions.ai import LLMGenerationError
from app.models.document_model import Document
from app.models.notebook_model import Notebook, NotebookSummary
from app.services.summary.models import Digest, DigestSource
from app.services.summary.token_batcher import TokenBatcher

logger = logging.getLogger(__name__)


class SummaryService:
    def __init__(
        self,
        sql_db: Session,
        mongo_db: AsyncIOMotorDatabase,
        chroma_client: ClientAPI,
        llm_client: LLMClient,
    ) -> None:
        self.sql_db = sql_db
        self.document_collection = mongo_db["parsed_documents"]
        self.notebook_summaries_collection = mongo_db["notebook_summaries"]
        self.chroma_client = chroma_client
        self.llm_client = llm_client
        self.token_batcher = TokenBatcher(max_tokens=18000)

    def _strip_markdown_fences(self, text: str) -> str:
        """Robustly remove ```json and ``` wrapping from LLM output."""
        text = text.strip()
        # Matches ```(optional format)\n ... \n``` safely
        pattern = r"^```(?:json)?\s*(.*?)\s*```$"
        match = re.match(pattern, text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text

    # ==================================================
    # RECURSIVE DOCUMENT DIGEST GENERATION
    # ==================================================

    async def _get_or_generate_document_digest(self, doc: Document) -> dict:
        """
        Fetch the Document Digest from Mongo cache.
        If missing, generate it recursively from raw Chroma chunks.
        Strictly validates output using the Digest model and source_refs.
        """
        if not doc.mongo_id:
            raise ValueError(f"Document {doc.id} missing mongo_id.")

        try:
            obj_id = ObjectId(doc.mongo_id)
        except Exception:
            obj_id = doc.mongo_id

        # Layer 1 Cache: Digest
        parsed_doc = await self.document_collection.find_one({"_id": obj_id})
        if parsed_doc and "document_digest" in parsed_doc:
            logger.info(f"Document Digest cache hit for Document {doc.id}")
            return parsed_doc["document_digest"]

        logger.info(f"Generating Document Digest for Document {doc.id}")

        try:
            collection = self.chroma_client.get_collection(
                name=settings.CHROMA_COLLECTION_NAME
            )
        except Exception as e:
            raise ValueError(
                f"Chroma collection '{settings.CHROMA_COLLECTION_NAME}' does not exist. "
                f"Ensure the pipeline has run. Error: {str(e)}"
            )

        results = collection.get(where={"document_id": doc.id})

        ids = results.get("ids", [])
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])

        logger.info(
            f"[Digest Debug] Document={doc.id} " f"Chroma chunks={len(documents)}"
        )

        if documents:
            logger.info(f"[Digest Debug] First chunk length={len(documents[0])} chars")

            for i, chunk in enumerate(documents[:3]):
                logger.info(f"[Digest Debug] Chunk {i}: {chunk[:300]}")

        # Empty document
        if not ids or not documents:
            logger.warning(
                f"No chunks found in Chroma for Document {doc.id}. Caching empty digest."
            )

            empty_digest = {
                "title": doc.title,
                "overview": "Tài liệu không có nội dung.",
                "key_concepts": [],
                "entities": [],
                "formulas": [],
                "relationships": [],
                "keywords": [],
                "source_refs": [],
            }

            result = await self.document_collection.update_one(
                {"_id": obj_id},
                {
                    "$set": {
                        "document_digest": empty_digest,
                        "generated_at": datetime.now(UTC),
                    }
                },
            )

            if result.matched_count == 0:
                raise LLMGenerationError(f"Cannot cache digest for document {doc.id}")

            return empty_digest

        combined = list(zip(ids, documents, metadatas))
        combined.sort(key=lambda x: x[2].get("chunk_index", x[0]) if x[2] else x[0])

        units = [
            DigestSource(id=chunk_id, content=text) for chunk_id, text, _ in combined
        ]

        is_leaf = True
        current_level = 0

        # Recursive Digest Generation
        while is_leaf or len(units) > 1:
            batches = self.token_batcher.build(units)

            if not batches:
                raise LLMGenerationError(
                    f"TokenBatcher returned no batches for document {doc.id}"
                )

            logger.info(
                f"[Digest] Document={doc.id} Level={current_level} "
                f"Units={len(units)} Batches={len(batches)}"
            )

            next_units = []

            for i, batch in enumerate(batches):
                logger.info(
                    f"[Digest] Level={current_level} "
                    f"Batch={i + 1}/{len(batches)} "
                    f"Items={len(batch)}"
                )

                prompt = SummaryPromptBuilder.build_digest(
                    source_label=doc.title,
                    contents=batch,
                    is_leaf=is_leaf,
                )

                response_str = await self.llm_client.generate(prompt)

                if not response_str:
                    raise LLMGenerationError("LLM returned empty digest block.")

                cleaned_str = self._strip_markdown_fences(response_str)
                # Strict structural validation using the Digest Pydantic model
                try:
                    digest_obj = Digest.model_validate_json(cleaned_str)

                except ValidationError as e:
                    logger.exception(e)
                    logger.error(cleaned_str)
                    raise

                except Exception:
                    logger.exception("Unexpected")
                    logger.error(cleaned_str)
                    raise

                # Strict source_refs validation
                valid_ids = {u.id for u in batch}

                for ref in digest_obj.source_refs:
                    if ref not in valid_ids:
                        raise LLMGenerationError(
                            f"Hallucinated source_ref detected: '{ref}'. "
                            f"Valid sources: {valid_ids}"
                        )
                # Store validated content for the next recursive level
                next_units.append(
                    DigestSource(
                        id=f"digest_l{current_level}_b{i}",
                        content=digest_obj.model_dump_json(),
                    )
                )

                logger.info(
                    f"[Digest] Finished Level={current_level} "
                    f"Batch={i + 1}/{len(batches)}"
                )

            units = next_units

            logger.info(
                f"[Digest] Completed Level={current_level} " f"-> {len(units)} digests"
            )

            is_leaf = False
            current_level += 1
        # Final output format and caching in MongoDB
        final_digest_dict = json.loads(units[0].content)

        await self.document_collection.update_one(
            {"_id": obj_id},
            {
                "$set": {
                    "document_digest": final_digest_dict,
                    "generated_at": datetime.now(UTC),
                }
            },
        )

        logger.info(f"Document Digest generated successfully for Document {doc.id}")

        return final_digest_dict

    # ==================================================
    # 2. NOTEBOOK SUMMARY SYNTHESIS
    # ==================================================

    async def generate_notebook_summary(
        self,
        user_id: int,
        notebook_id: int,
        level: str,
        format_type: str,
        instruction: str,
    ) -> str:
        """
        Synthesize Notebook Summary using ONLY the active Document Digests.
        Applies a two-level cache strategy.
        """
        # 1. Authorize & fetch active documents
        notebook = (
            self.sql_db.query(Notebook)
            .filter(Notebook.id == notebook_id, Notebook.user_id == user_id)
            .first()
        )
        if not notebook:
            raise ValueError("Notebook not found or unauthorized.")

        active_docs = [
            nd.document for nd in notebook.notebook_documents if nd.is_active
        ]
        if not active_docs:
            raise ValueError("Không có tài liệu nào đang được bật trong Notebook này.")

        active_doc_ids = sorted([doc.id for doc in active_docs])

        # Check Notebook Summary Cache (Layer 2)
        existing_summaries = (
            self.sql_db.query(NotebookSummary)
            .filter(
                NotebookSummary.notebook_id == notebook_id,
                NotebookSummary.format == format_type,
                NotebookSummary.level == level,
                NotebookSummary.instruction == instruction,
            )
            .all()
        )

        for summary_record in existing_summaries:
            if summary_record.source_document_ids == active_doc_ids:
                mongo_doc = await self.notebook_summaries_collection.find_one(
                    {"_id": ObjectId(summary_record.mongo_summary_id)}
                )
                if mongo_doc and "summary_text" in mongo_doc:
                    logger.info(
                        f"Notebook Summary cache hit for Notebook {notebook_id}"
                    )
                    return mongo_doc["summary_text"]

        # Retrieve or build Document Digests
        document_digests = []
        for doc in active_docs:
            digest = await self._get_or_generate_document_digest(doc)
            document_digests.append(
                {
                    "title": doc.title,
                    "digest": digest,
                }
            )

        # 4. Final Synthesis
        logger.info(
            f"Synthesizing Notebook Summary for Notebook {notebook_id} "
            f"using {len(active_docs)} document digests."
        )

        prompt = SummaryPromptBuilder.build_notebook_summary(
            digests=document_digests,
            length=level,
            output_format=format_type,
            instruction=instruction,
        )

        final_summary = await self.llm_client.generate(prompt)
        if not final_summary:
            raise LLMGenerationError("LLM không trả về nội dung tóm tắt Notebook.")

        # 5. Cache Notebook Summary Output
        mongo_result = await self.notebook_summaries_collection.insert_one(
            {
                "summary_text": final_summary,
                "created_at": datetime.now(UTC),
            }
        )

        new_summary_record = NotebookSummary(
            notebook_id=notebook_id,
            title=f"Notebook Summary - {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}",
            mongo_summary_id=str(mongo_result.inserted_id),
            level=level,
            format=format_type,
            instruction=instruction,
            source_document_ids=active_doc_ids,
        )
        self.sql_db.add(new_summary_record)
        self.sql_db.commit()

        return final_summary
