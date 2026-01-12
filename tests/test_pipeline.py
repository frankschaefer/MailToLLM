from pathlib import Path

from mailtollm.core.pipeline import run_pipeline


def test_run_pipeline_creates_outputs(tmp_path: Path) -> None:
    csv_path = tmp_path / "emails.csv"
    csv_path.write_text(
        "id,subject,from,to,date,body\n"
        "email-1,Hello,sender@example.com,rcpt@example.com,2026-01-06,Contact me at test@example.com\n",
        encoding="utf-8",
    )

    attachments_root = tmp_path / "attachments"
    attachments_root.mkdir()

    output_dir = tmp_path / "output"

    outputs = run_pipeline(csv_path, attachments_root, output_dir)

    assert len(outputs) == 1
    assert (output_dir / "email-1.json").exists()
    assert (output_dir / "contacts_outlook.csv").exists()


def test_run_pipeline_skips_existing(tmp_path: Path) -> None:
    csv_path = tmp_path / "emails.csv"
    csv_path.write_text(
        "id,subject,from,to,date,body\n"
        "email-2,Hello,sender@example.com,rcpt@example.com,2026-01-06,Body\n",
        encoding="utf-8",
    )

    attachments_root = tmp_path / "attachments"
    attachments_root.mkdir()

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "email-2.json").write_text("{}", encoding="utf-8")

    outputs = run_pipeline(csv_path, attachments_root, output_dir)

    assert outputs == []


def test_run_pipeline_directory_structure(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    inbox_dir = input_root / "Inbox"
    inbox_dir.mkdir(parents=True)

    csv_path = inbox_dir / "emails.csv"
    csv_path.write_text(
        "id,subject,from,to,date,body\n"
        "email-3,Hello,sender@example.com,rcpt@example.com,2026-01-06,Body\n",
        encoding="utf-8",
    )

    attachments_root = tmp_path / "attachments"
    attachments_root.mkdir()

    output_dir = tmp_path / "output"

    outputs = run_pipeline(input_root, attachments_root, output_dir)

    assert len(outputs) == 1
    assert (output_dir / "Inbox" / "email-3.json").exists()


def test_run_pipeline_detail_logging(tmp_path: Path) -> None:
    csv_path = tmp_path / "emails.csv"
    csv_path.write_text(
        "id,subject,from,to,date,body\n"
        "email-4,Hello,sender@example.com,rcpt@example.com,2026-01-06,Body\n",
        encoding="utf-8",
    )

    attachments_root = tmp_path / "attachments"
    attachments_root.mkdir()
    output_dir = tmp_path / "output"

    logs: list[str] = []

    run_pipeline(
        csv_path,
        attachments_root,
        output_dir,
        detail_logging=True,
        on_log=logs.append,
    )

    assert any("Timing" in entry for entry in logs)
