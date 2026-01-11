from __future__ import annotations

from pathlib import Path

from mailtollm.models.schema import LLMOutput


def run_pipeline(csv_path: Path, attachments_root: Path, output_dir: Path) -> list[LLMOutput]:
    """Placeholder pipeline to be implemented.

    Steps:
    - Read CSV
    - Resolve attachment paths
    - Extract content by file type
    - Build LLMOutput per email
    - Write JSON outputs
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    return []
