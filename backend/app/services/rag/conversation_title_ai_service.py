# app/services/rag/conversation_title_ai_service.py

from __future__ import annotations

import logging

from app.ai.llm.base import LLMClient
from app.ai.output.conversation_title_parser import (
    ConversationTitleParseError,
    ConversationTitleParser,
)
from app.ai.prompts.conversation_title_prompt import (
    ConversationTitlePromptBuilder,
)

logger = logging.getLogger(__name__)


class ConversationTitleAIService:
    """
    Generate a title for a conversation from its first user message.

    This service is deliberately small and side-effect free with respect to
    database state.

    Responsibilities:
    - Build the title-generation prompt.
    - Call the configured LLM.
    - Parse and validate the generated title.
    - Gracefully fail without affecting the main chat flow.

    NOT responsible for:
    - Determining whether this is the first conversation message.
    - Reading or updating Conversation models.
    - Persisting titles.
    - Protecting manually renamed titles.
    - Creating background tasks.
    """

    def __init__(
        self,
        *,
        llm_client: LLMClient,
        prompt_builder: type[ConversationTitlePromptBuilder] = (
            ConversationTitlePromptBuilder
        ),
        parser: type[ConversationTitleParser] = ConversationTitleParser,
    ):
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder
        self.parser = parser

    async def generate_title(
        self,
        *,
        first_user_message: str,
    ) -> str | None:
        """
        Generate a conversation title.

        Returns:
            A validated title on success.
            None if title generation fails.

        Failure is intentionally non-fatal because conversation title
        generation must never break the main Assistant message flow.
        """

        message = first_user_message.strip()

        if not message:
            logger.warning(
                "Skipping conversation title generation: "
                "first user message is empty."
            )
            return None

        try:
            prompt = self.prompt_builder.build(
                first_user_message=message,
            )

            raw_response = await self.llm_client.generate(
                prompt=prompt,
            )

            if not raw_response or not raw_response.strip():
                logger.warning(
                    "Conversation title generation returned an empty response."
                )
                return None

            title = self.parser.parse(raw_response)

            logger.info(
                "Conversation title generated successfully: %s",
                title,
            )

            return title

        except ConversationTitleParseError as exc:
            logger.warning(
                "Failed to parse generated conversation title: %s",
                exc,
            )
            return None

        except Exception:
            # Title generation is secondary functionality.
            # Do not propagate this into the main chat request.
            logger.exception(
                "Unexpected error while generating conversation title."
            )
            return None
