from app.ai.llm.base import LLMClient
from app.ai.output.classifier_parser import ClassifierOutputParser
from app.ai.prompts.classifier_prompt import ClassifierPromptBuilder
from app.services.document.models import DocumentAIClassification


class AIClassifier:
    """
    Orchestrates the document classification workflow via Gemini.
    """

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def _extract_representative_text(self, raw_text: str, max_chars: int = 12000) -> str:
        if len(raw_text) <= max_chars:
            return raw_text

        head_size = int(max_chars * 0.40)
        mid_size = int(max_chars * 0.30)
        tail_size = int(max_chars * 0.30)

        # Trích xuất phần đầu và ngắt theo dòng gần nhất
        head_end = raw_text.rfind("\n", 0, head_size)
        head = raw_text[: head_end if head_end != -1 else head_size]

        # Trích xuất phần giữa xung quanh điểm trung tâm tài liệu
        center = len(raw_text) // 2
        mid_start_raw = max(0, center - (mid_size // 2))
        mid_start = raw_text.find("\n", mid_start_raw)
        if mid_start == -1 or mid_start >= center:
            mid_start = mid_start_raw

        mid_end = raw_text.rfind("\n", mid_start, mid_start + mid_size)
        middle = raw_text[mid_start : mid_end if mid_end != -1 else mid_start + mid_size]

        # Trích xuất phần cuối tài liệu
        tail_start_raw = max(0, len(raw_text) - tail_size)
        tail_start = raw_text.find("\n", tail_start_raw)
        tail = raw_text[tail_start if tail_start != -1 else tail_start_raw :]

        return f"{head.strip()}\n\n[...]\n\n{middle.strip()}\n\n[...]\n\n{tail.strip()}"

    async def classify(self, raw_text: str) -> DocumentAIClassification:
        """
        Analyze the document text and return deterministic classification metadata.
        """
        if not raw_text:
            return DocumentAIClassification(
                categories=[], language="other", purpose="reference", keywords=[]
            )

        sampled_text = self._extract_representative_text(raw_text)
        prompt = ClassifierPromptBuilder.build(sampled_text)
        raw_response = await self.llm_client.generate(prompt)
        return ClassifierOutputParser.parse(raw_response)