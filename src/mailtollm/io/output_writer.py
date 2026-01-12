from __future__ import annotations

import json
from pathlib import Path

from mailtollm.models.schema import LLMOutput


def read_output_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_output_json(output_dir: Path, output: LLMOutput) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{output.email.id}.json"
    payload = output.model_dump()
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path
