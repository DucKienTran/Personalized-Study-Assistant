from app.ai.constants import (
    CATEGORY_DESCRIPTIONS,
    PURPOSE_DEFINITIONS,
    Category,
    Language,
    Purpose,
)


class ClassifierPromptBuilder:
    """
    Build the prompt for document-level classification.
    Accepts only the raw text string from the processed document.
    """

    @staticmethod
    def build(markdown: str) -> str:
        categories_str = "\n".join(
            f"- {category.value}: {CATEGORY_DESCRIPTIONS[category]}" for category in Category
        )

        purposes_str = "\n".join(
            f"- {purpose.value}: {PURPOSE_DEFINITIONS[purpose]}" for purpose in Purpose
        )

        languages_str = ", ".join(language.value for language in Language)

        return f"""
You are an AI document classifier.
Your task is to classify the ENTIRE document content.
Return ONLY valid JSON. Do not write explanation. Never return Markdown code blocks.

========================
Supported Categories
========================
{categories_str}

========================
Supported Purposes
========================
{purposes_str}

========================
Supported Languages
========================
{languages_str}

========================
Rules
========================
- Categories must come ONLY from the supported list.
- Purpose must be exactly ONE supported value.
- Language must be exactly ONE supported value.
- Keywords should contain 5-10 important concepts representing the text.
- Do not invent information.

========================
JSON Schema Output
========================
{{
    "categories": ["computer_science"],
    "language": "en",
    "purpose": "learning_material",
    "keywords": ["TCP", "Congestion Control", "Sliding Window"]
}}

========================
Document Content
========================
{markdown}
"""
