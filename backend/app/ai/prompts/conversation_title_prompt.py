# app/ai/prompts/conversation_title_prompt.py

from __future__ import annotations


class ConversationTitlePromptBuilder:
    """
    Build the LLM prompt used to generate a short conversation title.

    Responsibilities:
    - Inject the first user message.
    - Define title quality rules.
    - Enforce a minimal JSON output schema.

    NOT responsible for:
    - Calling the LLM.
    - Parsing the LLM response.
    - Saving the title.
    - Deciding whether a conversation is eligible for title generation.
    """

    @staticmethod
    def build(*, first_user_message: str) -> str:
        message = first_user_message.strip()

        if not message:
            raise ValueError("first_user_message cannot be empty.")

        return f"""
You generate concise titles for chat conversations.

Your task is to create ONE short title that accurately describes the main topic
of the user's first message.

==============================
USER MESSAGE
==============================

{message}

==============================
TITLE REQUIREMENTS
==============================

1. Describe the main topic of the conversation clearly.

2. Use the SAME language as the user's message whenever possible.

3. Keep the title concise.
   Prefer 3-7 words when that is natural.

4. Do not copy the entire user message.

5. Do not answer the user's question.

6. Do not add information that is not present or reasonably implied by the
   user's message.

7. Do not prefix the title with:
   - "Title:"
   - "Conversation:"
   - "Topic:"
   - or equivalent wording in any language.

8. Do not wrap the title in quotation marks.

9. Do not end the title with unnecessary punctuation.

10. Do not use Markdown.

==============================
OUTPUT FORMAT
==============================

Return ONLY ONE valid JSON object:

{{
    "title": "..."
}}

Rules:

- "title" MUST be a non-empty string.
- No Markdown.
- No code fences.
- No explanations.
- No additional keys.
- The response must be directly parseable as JSON.
""".strip()
