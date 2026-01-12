from pathlib import Path

from mailtollm.io.csv_reader import read_email_csv


def test_read_email_csv_posteingang_structure(tmp_path: Path) -> None:
    csv_path = tmp_path / "posteingang.csv"
    csv_path.write_text(
        "Date,Subject,Body,From:,To:,CC:,Attachments:,Attachments Path:\n"
        "1/6/2026 1:46:49 PM,Subj,Body,from@example.com,to1@example.com; to2@example.com,cc@example.com,file1.pdf; image.png,/tmp/Attachments\n",
        encoding="utf-8",
    )

    records = read_email_csv(csv_path)

    assert records[0]["sender"] == "from@example.com"
    assert records[0]["recipients"] == ["to1@example.com", "to2@example.com", "cc@example.com"]
    assert records[0]["attachment_names"] == ["file1.pdf", "image.png"]
    assert records[0]["folder"] == "/tmp/Attachments"
