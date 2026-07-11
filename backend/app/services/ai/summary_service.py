import logging

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.ai.llm.base import LLMClient
from app.ai.prompts.summary_prompt import SummaryPromptBuilder
from app.exceptions.ai import LLMGenerationError

logger = logging.getLogger(__name__)


class SummaryService:
    def __init__(
        self,
        mongo_db: AsyncIOMotorDatabase,
        llm_client: LLMClient,
    ) -> None:
        self.document_collection = mongo_db["parsed_documents"]
        self.llm_client = llm_client

    async def generate_summary(
        self,
        mongo_id: str,
        level: str,
        format_type: str,
        instruction: str,
    ) -> str:
        parsed_document = await self.document_collection.find_one({"_id": ObjectId(mongo_id)})

        if not parsed_document or "content_raw" not in parsed_document:
            raise ValueError("Không tìm thấy nội dung tài liệu trong MongoDB.")

        content_raw = parsed_document["content_raw"]

        safe_instruction = instruction.strip().replace(".", "").replace(" ", "_")[:20]

        cache_key = (f"{level}_{format_type}_{safe_instruction}").lower()

        summaries = parsed_document.get("summaries", {})

        if cache_key in summaries:
            logger.info(
                "Summary cache hit. key=%s",
                cache_key,
            )
            return summaries[cache_key]

        prompt = SummaryPromptBuilder.build(
            content=content_raw,
            level=level,
            format_type=format_type,
            instruction=instruction,
        )

        logger.info(
            "Generating summary from LLM. key=%s",
            cache_key,
        )

        ai_response = await self.llm_client.generate(prompt)

        if not ai_response:
            raise LLMGenerationError("LLM không trả về nội dung tóm tắt.")

        await self.document_collection.update_one(
            {"_id": ObjectId(mongo_id)},
            {
                "$set": {
                    f"summaries.{cache_key}": ai_response,
                }
            },
        )

        logger.info(
            "Summary generated successfully. key=%s",
            cache_key,
        )

        return ai_response
