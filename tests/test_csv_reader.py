from pathlib import Path

from mailtollm.io.csv_reader import read_email_csv


def test_read_email_csv_outlook_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "emails.csv"
    csv_path.write_text(
        "From: (Name),From: (Address),To: (Name),To: (Address),Subject,Body\n"
        "Jane Doe,jane@example.com,John Doe,john@example.com,Hello,Body text\n",
        encoding="utf-8",
    )

    records = read_email_csv(csv_path)

    assert records[0]["sender"] == "Jane Doe <jane@example.com>"
    assert records[0]["recipients"] == ["John Doe <john@example.com>"]
    assert records[0]["subject"] == "Hello"
