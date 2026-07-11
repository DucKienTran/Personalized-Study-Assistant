import logging

import google.generativeai as genai

from app.ai.llm.base import LLMClient
from app.core.config import settings
from app.exceptions.ai import (
    AIConfigurationError,
    EmptyLLMResponseError,
    LLMGenerationError,
)

logger = logging.getLogger(__name__)


class GeminiClient(LLMClient):
    """
    Concrete implementation của LLMClient sử dụng Google Gemini.
    """

    def __init__(self) -> None:
        api_key = settings.GEMINI_API_KEY

        if not api_key:
            raise AIConfigurationError("GEMINI_API_KEY chưa được cấu hình.")

        genai.configure(api_key=api_key)

        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    async def generate(self, prompt: str) -> str:
        """
        Gửi prompt tới Gemini và trả về nội dung text.

        Raises:
            LLMGenerationError:
                Khi Gemini trả về rỗng hoặc phát sinh lỗi.
        """
        try:
            logger.info("Generating response from Gemini...")

            response = await self.model.generate_content_async(prompt)

            if not response or not response.text:
                raise EmptyLLMResponseError()

            logger.info(
                "Gemini generation completed successfully (%d characters).",
                len(response.text),
            )

            return response.text

        except LLMGenerationError:
            raise

        except Exception as exc:
            logger.exception("Gemini generation failed.")
            raise LLMGenerationError(f"Lỗi khi gọi Gemini: {exc}") from exc
