import json

from app.schemas.dashboard_schema import CandidateStatForPrompt


class DashboardInsightPromptBuilder:
    @staticmethod
    def build(candidates: list[CandidateStatForPrompt]) -> str:
        payload = [candidate.model_dump() for candidate in candidates]
        return f"""
You are a concise, encouraging learning coach. Select 1 to 3 of the most noteworthy
statistics from the JSON below and write one or two short sentences about them.

Rules:
- Use only facts present in the JSON. Never infer or invent a number.
- If you mention a number or formatted value, copy the candidate's `value` exactly.
- Mention every selected statistic using the exact `label: value` pair from the input.
- Return only valid JSON with this exact shape:
  {{"text": "...", "selected_keys": ["exact_candidate_key"]}}
- Every selected key must come from the input and every selected statistic should be
  reflected in the text.
- Keep the tone warm and constructive. Do not use markdown.

Candidate statistics:
{json.dumps(payload, ensure_ascii=True, separators=(",", ":"))}
""".strip()
