from pathlib import Path

from mailtollm.io.attachment_resolver import resolve_attachment_paths


def test_resolve_attachment_paths_absolute_folder_hint(tmp_path: Path) -> None:
    attachments_root = tmp_path / "root"
    attachments_root.mkdir()

    hint_dir = tmp_path / "Attachments"
    hint_dir.mkdir()
    file_path = hint_dir / "file.pdf"
    file_path.write_text("data", encoding="utf-8")

    resolved = resolve_attachment_paths(attachments_root, str(hint_dir), ["file.pdf"])

    assert resolved == [file_path]
