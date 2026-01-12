from __future__ import annotations

from pathlib import Path


def resolve_attachment_paths(
    attachments_root: Path, folder_hint: str, attachment_names: list[str]
) -> list[Path]:
    base = attachments_root
    if folder_hint:
        hint_path = Path(folder_hint).expanduser()
        if hint_path.is_absolute() and hint_path.exists():
            base = hint_path
        else:
            candidate = attachments_root / folder_hint
            if candidate.exists():
                base = candidate

    resolved: list[Path] = []
    for name in attachment_names:
        candidate = Path(name)
        if candidate.is_absolute():
            if candidate.exists():
                resolved.append(candidate)
            continue
        path = base / name
        if path.exists():
            resolved.append(path)
    return resolved
