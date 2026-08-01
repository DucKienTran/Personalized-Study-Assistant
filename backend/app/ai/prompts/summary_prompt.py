from __future__ import annotations

import json

from app.services.summary.models import DigestSource


class SummaryPromptBuilder:
    @staticmethod
    def build_digest(
        source_label: str,
        contents: list[DigestSource],
        is_leaf: bool,
    ) -> str:
        """
        Build a semantic Digest.

        Used recursively:
        - Raw Chunks -> Digest
        - Digests -> Bigger Digest
        """

        source_description = (
            "The following sources are raw document chunks."
            if is_leaf
            else "The following sources are previously generated semantic digests."
        )

        schema = {
            "title": "...",
            "overview": "...",
            "key_concepts": [],
            "entities": [],
            "formulas": [],
            "relationships": [
                {
                    "source": "...",
                    "target": "...",
                    "type": "related",
                    "description": "...",
                }
            ],
            "keywords": [],
            "source_refs": [],
        }

        example_good = [
            "Entity A",
            "Entity B",
        ]

        example_bad = [
            {
                "name": "Entity A",
                "description": "...",
            }
        ]

        sources = []

        for item in contents:
            sources.append(
                f"""
Source ID:
{item.id}

Content:
{item.content}
"""
            )

        return f"""
You are an AI system responsible for building an INTERNAL semantic digest.

This digest is NOT intended for end users.
It is an intermediate knowledge representation that will later be used to generate summaries, quizzes, flashcards and other learning materials.

{source_description}

Document:
{source_label}

Requirements

- Never invent facts.
- Preserve every important concept.
- Preserve technical terminology.
- Merge duplicated information.
- Preserve semantic relationships.
- Keep the output concise but information-dense.
- source_refs MUST contain ONLY the Source IDs provided below.
- Output ONLY valid JSON.
- The JSON MUST exactly follow the schema below.
- Do NOT enrich the schema.
- Do NOT add extra fields.
- Do NOT replace strings with objects.
- Every value MUST match the declared JSON type exactly.

Digest Schema

{json.dumps(schema, indent=2)}

IMPORTANT

You MUST follow the schema EXACTLY.

The data types are mandatory.

Example of CORRECT entities:

{json.dumps(example_good, indent=2)}

Example of INCORRECT entities:

{json.dumps(example_bad, indent=2)}

If a field is defined as list[str], every element MUST be a plain string.

Do NOT introduce additional keys.

Do NOT change any field types.

If you are unsure, return an empty list instead of inventing a different structure.

Sources

{chr(10).join(sources)}
"""

    @staticmethod
    def build_notebook_summary(
        digests: list[dict],
        length: str,
        output_format: str,
        instruction: str | None = None,
    ) -> str:
        """
        Generate the final notebook summary.

        length:
            brief | standard | comprehensive

        output_format:
            markdown | raw_text
        """

        length_map = {
            "brief": """
Generate a concise summary.
Target length: approximately 200–400 words.
Include only the most important concepts and conclusions.
""",
            "standard": """
Generate a balanced summary.
Target length: approximately 600–1000 words.
Cover all major concepts while avoiding unnecessary repetition.
""",
            "comprehensive": """
Generate a comprehensive study summary.
Preserve important explanations, relationships, examples and context.
Do not omit concepts necessary for understanding.
""",
        }

        format_map = {
            "markdown": """
Output using Markdown.
Use headings, lists, tables and emphasis where appropriate.
""",
            "raw_text": """
Output plain raw text only.
Do not use Markdown syntax.
""",
        }

        docs = []

        for digest in digests:
            docs.append(
                f"""
Document:
{digest["title"]}

Digest:
{json.dumps(digest["digest"], ensure_ascii=False, indent=2)}
"""
            )

        instruction_text = (
            f"\nAdditional user instruction:\n{instruction}"
            if instruction
            else ""
        )

        return f"""
You are an AI learning assistant.

Your task is to generate ONE unified notebook summary from multiple document digests.

The digests are structured semantic representations, not raw document text.

Objectives

- Merge duplicated concepts across documents.
- Connect complementary concepts.
- Identify prerequisite relationships when possible.
- Identify contradictions when documents disagree, and explicitly mention the related document titles.
- Preserve important terminology.
- Produce a coherent knowledge flow instead of summarizing each document independently.
- Never invent information.

Summary Length

{length_map.get(length.lower(), length_map["standard"])}

Output Format

{format_map.get(output_format.lower(), format_map["markdown"])}

{instruction_text}

Document Digests

{chr(10).join(docs)}
"""