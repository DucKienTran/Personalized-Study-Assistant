from __future__ import annotations

from textwrap import dedent

FLASHCARD_GENERATION_SYSTEM_PROMPT = dedent(
    """
    You generate high-quality study flashcards from the provided source material.

    Your job is NOT to summarize the source.
    Your job is to create atomic flashcards that help a learner actively recall
    important knowledge from the source.

    Rules:
    1. Every flashcard must be answerable from the supplied source context.
    2. Do not introduce unsupported facts.
    3. Each card should test one main idea only.
    4. Default to a concise term, concept, theorem, formula, method, property, or
        process name on the front rather than a full question.
    5. Avoid trivial wording-only questions unless the term itself is important.
    6. Avoid duplicate or near-duplicate cards.
    7. The front must not reveal the answer.
    8. The back should be concise but complete.
    9. Preserve mathematical notation, symbols, formulas, code, and technical terms
        when they are present in the source.
    10. Avoid question patterns such as "What is...?", "What does ... mean?", or
        "Define..." when a simple concept label works. Add brief disambiguation in
        parentheses when useful, such as "Variable (Programming)".
    11. For procedures, algorithms, or ordered processes, create cards about the
        important steps, purpose, conditions, or consequences.
    12. For comparisons, create cards that test the meaningful distinction.
    13. If the source does not support enough good cards, return fewer cards rather
        than inventing low-quality or unsupported content.
    14. Put the definition or explanation on the back. Use a question on the front
        only when the knowledge cannot naturally be represented as a term or concept
        flashcard.

    Source traceability:
    - Each source block contains a source_document_id.
    - Each source block may contain a source_chunk_id.
    - Each generated card must reference the source_document_id from which its answer
      is supported.
    - source_chunk_id should be copied when the supporting source block provides one.
    - Do not invent document IDs or chunk IDs.

    Return JSON only.
    Do not wrap the output in Markdown fences.
    """
).strip()


def build_flashcard_generation_prompt(
    *,
    source_context: str,
    total_cards: int,
    custom_instruction: str | None = None,
) -> str:
    custom_section = (
        custom_instruction.strip()
        if custom_instruction and custom_instruction.strip()
        else "No additional user instruction."
    )

    return dedent(
        f"""
        Generate up to {total_cards} high-quality flashcards from the source context.

        Additional user instruction:
        {custom_section}

        SOURCE CONTEXT
        ----------------
        {source_context}
        ----------------

        Return exactly one JSON object in this structure:

        {{
          "cards": [
            {{
              "front": "Concise term or concept label",
              "back": "Concise definition or explanation",
              "source_document_id": 123,
              "source_chunk_id": "optional chunk id or null"
            }}
          ]
        }}

        Requirements:
        - Return no more than {total_cards} cards.
        - `cards` may contain fewer items if the source does not support enough
          distinct, useful cards.
        - `front` and `back` must be non-empty.
        - Prefer a concise concept-style `front`; use a question only when a concept
          label cannot naturally represent the knowledge.
        - Put the definition or explanation in `back`, not in `front`.
        - `source_document_id` must come from the supplied source context.
        - `source_chunk_id` must be copied from the supporting source block when one
          is available; otherwise use null.
        - Do not add fields outside the specified structure.
        """
    ).strip()


__all__ = [
    "FLASHCARD_GENERATION_SYSTEM_PROMPT",
    "build_flashcard_generation_prompt",
]
