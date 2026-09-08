from __future__ import annotations


class AssistantActionPromptBuilder:
    """
    Phase-2 router prompt.

    Keep the action space deliberately small:
    - answer: normal Assistant/RAG response, including questions about how the app works.
    - create_summary: user explicitly asks to create/generate/summarize the active notebook.
    - create_mindmap: user explicitly asks to create/generate a mindmap.

    Phase 2 routes explicit Quiz and Flashcard creation requests.
    """

    @staticmethod
    def build(*, user_message: str) -> str:
        return f"""
You are an intent router for a learning web application.

Choose exactly ONE action:
- "answer": normal question/answer, including explanations about how the website or its features work.
- "create_summary": the user explicitly asks the app to create/generate a summary of the current notebook/material.
- "create_mindmap": the user explicitly asks the app to create/generate a mindmap of the current notebook/material.
- "create_quiz": the user explicitly asks to create/generate a quiz, test, or set of quiz questions.
- "create_flashcards": the user explicitly asks to create/generate flashcards or a flashcard deck.

Important:
- Do NOT classify a question ABOUT summaries or mindmaps as a create action.
- "What is a mindmap?" => answer
- "How does Summary work?" => answer
- "Create a mindmap for me" => create_mindmap
- "Summarize this notebook" => create_summary
- "Quiz hoạt động như thế nào?" => answer
- "Flashcard là gì?" => answer
- "Tạo quiz cho tôi" => create_quiz
- "Create a 20-question quiz" => create_quiz
- "Tạo flashcards cho tôi" => create_flashcards
- "Create 15 flashcards about duality" => create_flashcards
- Missing generation settings use safe defaults later; do not ask clarification questions.
- When uncertain, choose "answer".
- Return JSON only. No markdown.

Schema:
{{
  "action": "answer" | "create_summary" | "create_mindmap" | "create_quiz" | "create_flashcards",
  "confidence": 0.0,
  "reason": "short reason"
}}

User message:
{user_message}
""".strip()
