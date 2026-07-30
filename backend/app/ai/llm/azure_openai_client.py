import logging

from openai import AsyncOpenAI

from app.ai.llm.base import LLMClient
from app.core.config import settings
from app.exceptions.ai import (
    AIConfigurationError,
    EmptyLLMResponseError,
    LLMGenerationError,
)

logger = logging.getLogger(__name__)


class AzureOpenAIClient(LLMClient):
    """
    Concrete implementation của LLMClient sử dụng Azure OpenAI.
    """

    def __init__(self) -> None:
        api_key = settings.AZURE_OPENAI_API_KEY

        if not api_key:
            raise AIConfigurationError(
                "AZURE_OPENAI_API_KEY chưa được cấu hình."
            )

        if not settings.AZURE_OPENAI_BASE_URL:
            raise AIConfigurationError(
                "AZURE_OPENAI_BASE_URL chưa được cấu hình."
            )

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.AZURE_OPENAI_BASE_URL,
        )

        self.model = settings.AZURE_OPENAI_CHAT_MODEL

    async def generate(self, prompt: str) -> str:
        """
        Gửi prompt tới Azure OpenAI và trả về nội dung text.

        Raises:
            LLMGenerationError:
                Khi Azure OpenAI trả về rỗng hoặc phát sinh lỗi.
        """
        try:
            logger.info("Generating response from Azure OpenAI...")

            response = await self.client.responses.create(
                model=self.model,
                input=prompt,
            )

            if not response.output_text:
                raise EmptyLLMResponseError()

            logger.info(
                "Azure OpenAI generation completed successfully (%d characters).",
                len(response.output_text),
            )

            return response.output_text

        except LLMGenerationError:
            raise

        except Exception as exc:
            logger.exception("Azure OpenAI generation failed.")
            raise LLMGenerationError(
                f"Lỗi khi gọi Azure OpenAI: {exc}"
            ) from exc

    async def generate_stream(self, prompt: str):
        try:
            logger.info("Streaming response from Azure OpenAI...")

            stream = await self.client.responses.create(
                model=self.model,
                input=prompt,
                stream=True,
            )

            async for event in stream:
                if (
                    event.type == "response.output_text.delta"
                    and event.delta
                ):
                    yield event.delta

        except Exception as exc:
            logger.exception("Azure OpenAI streaming failed.")
            raise LLMGenerationError(
                f"Lỗi khi stream Azure OpenAI: {exc}"
            ) from exc