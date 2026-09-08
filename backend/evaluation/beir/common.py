from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from app.core.config import settings

BEIR_DATA_ROOT = Path(__file__).resolve().parent / "data"
BEIR_RESULTS_ROOT = Path(__file__).resolve().parent / "results"


def collection_name(dataset: str) -> str:
    safe_dataset = re.sub(r"[^a-z0-9_-]+", "_", dataset.lower())
    return f"{settings.CHROMA_COLLECTION_NAME}__beir_{safe_dataset}"


def manifest_path(dataset: str) -> Path:
    return BEIR_DATA_ROOT / dataset / "index_manifest.json"


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            check=True,
            text=True,
            timeout=2,
        )
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def write_json_once(directory: Path, experiment: str, payload: dict[str, Any]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    safe_experiment = re.sub(r"[^A-Za-z0-9_.-]+", "_", experiment).strip("._")
    if not safe_experiment:
        raise ValueError("Experiment label must contain at least one letter or number.")
    path = directory / f"{safe_experiment}_{timestamp}.json"
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return path


class OfflineRedis:
    """Request-local cache adapter that never touches production Redis."""

    async def get(self, key: str) -> None:
        return None

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        return True
