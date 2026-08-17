import asyncio
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
            raise AIConfigurationError("AZURE_OPENAI_API_KEY chưa được cấu hình.")

        if not settings.AZURE_OPENAI_BASE_URL:
            raise AIConfigurationError("AZURE_OPENAI_BASE_URL chưa được cấu hình.")

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
                max_output_tokens=settings.AZURE_OPENAI_MAX_OUTPUT_TOKENS,
            )

            logger.info(
                "Azure OpenAI response status=%s usage=%s incomplete_details=%s",
                getattr(response, "status", None),
                getattr(response, "usage", None),
                getattr(response, "incomplete_details", None),
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
            raise LLMGenerationError(f"Lỗi khi gọi Azure OpenAI: {exc}") from exc

    async def generate_stream(self, prompt: str):
        """
        Cancellation: `stream` is opened via `async with` so that if this
        generator is cancelled or closed early (caller hit Stop -> upstream
        asyncio.CancelledError), __aexit__ still runs and the underlying
        HTTP connection to Azure OpenAI is properly closed instead of left
        dangling — without this, cancelling the caller doesn't actually
        stop Azure from continuing to generate (and bill for) tokens no one
        is reading anymore.
        """
        try:
            logger.info("Streaming response from Azure OpenAI...")

            stream = await self.client.responses.create(
                model=self.model,
                input=prompt,
                stream=True,
            )

            async with stream:
                async for event in stream:
                    if event.type == "response.output_text.delta" and event.delta:
                        yield event.delta

        except asyncio.CancelledError:
            logger.info("Azure OpenAI streaming cancelled by caller.")
            raise

        except Exception as exc:
            logger.exception("Azure OpenAI streaming failed.")
            raise LLMGenerationError(f"Lỗi khi stream Azure OpenAI: {exc}") from exc
