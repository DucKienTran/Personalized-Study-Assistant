from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class MindmapSource:
    document_id: int
    document_title: str
    chunk_id: str
    content: str


class MindmapPromptBuilder:
    @staticmethod
    def build(
        notebook_title: str,
        sources: list[MindmapSource],
        max_nodes: int,
        max_depth: int,
        max_children_per_node: int,
    ) -> str:
        schema = {
            "id": "root",
            "label": "Main topic",
            "children": [
                {
                    "id": "node-1",
                    "label": "Important concept",
                    "children": [],
                }
            ],
        }

        formatted_sources = []
        for source in sources:
            formatted_sources.append(
                f"""
Source ID:
{source.chunk_id}

Document ID:
{source.document_id}

Document:
{source.document_title}

Content:
{source.content}
"""
            )

        return f"""
You are an AI learning assistant responsible for generating a visual knowledge mindmap.

Create a concise, easy-to-read knowledge tree that provides a visual overview of the notebook. It is not a detailed summary.

Notebook:
{notebook_title}

Output Requirements

- Output ONLY valid JSON.
- Follow the schema exactly.
- Do not add fields or text outside the JSON.
- Every node MUST contain exactly three fields: `id`, `label`, and `children`.
- `id` MUST be a non-empty string and unique across the entire tree.
- `label` MUST be a non-empty string.
- `children` MUST be an array on EVERY node, including leaf nodes.
- Never omit `children`; use an empty array for a leaf node.

Output Schema

{json.dumps(schema, indent=2)}

Mindmap Rules

- The root node represents the notebook's overall topic.
- Maximum total nodes: {max_nodes}
- The root node counts toward this limit.
- Maximum tree depth: {max_depth}
- The root node is depth 1.
- Maximum direct children per node: {max_children_per_node}
- The children limit applies to every node, including the root.
- Treat maximum depth as a safety ceiling, NOT a target.
- Do NOT optimize for visual symmetry, equal branch depth, or a balanced-looking tree.
- Sibling branches are explicitly allowed and expected to terminate at different depths.
- Expand a branch ONLY when the provided sources contain a meaningful substructure for that concept.
- If a concept is already sufficiently represented, leave `children` empty even when neighboring branches continue deeper.
- Do NOT add filler nodes, generic intermediate nodes, or redundant details just to make branches reach similar depths.
- It is undesirable for every top-level branch to have the same depth unless the source material genuinely requires it.
- A simple topic may end after one or two levels while a complex topic may continue much deeper.
- Prioritize high-level concepts first, then add deeper levels only where they improve understanding.
- Merge closely related concepts instead of creating excessive siblings.
- When both structures are semantically valid, prefer a deeper parent-child hierarchy over giving one node many direct children; create many siblings only when those concepts are genuinely parallel.
- If a concept would require more than {max_children_per_node} direct children, group related children under meaningful intermediate concepts.
- Avoid excessive leaf-level detail.
- Keep labels concise, ideally 2-8 words.
- Do not write long paragraphs in nodes.
- Never invent facts.
- Use only information contained in the provided sources.
- Preserve important technical terminology.
- When sources contain many details, select the most important concepts instead of trying to include everything.

Sources

{chr(10).join(formatted_sources)}
""".strip()
