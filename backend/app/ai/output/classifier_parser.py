import json

from pydantic import ValidationError

from app.ai.output.classifier_output import ClassifierOutput
from app.exceptions import ClassifierParseError
from app.services.document.models import DocumentAIClassification


class ClassifierOutputParser:
    """
    Parse raw Gemini output into a validated
    DocumentAIClassification.
    """

    @staticmethod
    def parse(raw_response: str) -> DocumentAIClassification:
        cleaned = raw_response.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json")
            cleaned = cleaned.removeprefix("```")
            cleaned = cleaned.removesuffix("```")
            cleaned = cleaned.strip()

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ClassifierParseError(f"Gemini returned invalid JSON: {e}") from e

        try:
            output = ClassifierOutput.model_validate(payload)
        except ValidationError as e:
            raise ClassifierParseError(
                f"Gemini returned an invalid classification schema: {e}"
            ) from e

        return DocumentAIClassification(
            categories=output.categories,
            language=output.language,
            purpose=output.purpose,
        )
