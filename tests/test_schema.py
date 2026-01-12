from mailtollm.models.schema import (
    AttachmentContent,
    AttachmentMeta,
    ContactExportRecord,
    EmailRecord,
    EntityIndex,
    LLMOutput,
    WarningRecord,
)


def test_llm_output_defaults() -> None:
    email = EmailRecord(
        id="email-1",
        subject="Subject",
        sender="sender@example.com",
        recipients=["a@example.com"],
        date="2026-01-06T15:35:00",
        body_text="Body",
        body_html=None,
        attachments=[
            AttachmentMeta(
                id="att-1",
                filename="file.pdf",
                path="/tmp/file.pdf",
                mime_type="application/pdf",
                size_bytes=123,
            )
        ],
    )

    output = LLMOutput(email=email)

    assert output.warnings == []
    assert output.attachment_contents == []
    assert output.entities == EntityIndex()
    assert output.contacts_export == []
    assert output.summary_text == ""
    assert output.combined_context == ""


def test_llm_output_with_warning() -> None:
    email = EmailRecord(
        id="email-2",
        subject="Subject",
        sender="sender@example.com",
        recipients=["b@example.com"],
        date="2026-01-06T15:35:00",
        body_text="Body",
        body_html=None,
    )

    warning = WarningRecord(
        attachment_id="att-2",
        code="UNREADABLE",
        message="Nicht lesbar",
        details="Encrypted PDF",
    )

    output = LLMOutput(
        email=email,
        warnings=[warning],
        attachment_contents=[AttachmentContent(id="att-2", text="", ocr_text="")],
        entities=EntityIndex(emails=["sender@example.com"]),
        contacts_export=[ContactExportRecord(source="email", email="sender@example.com")],
        combined_context="context",
    )

    assert output.warnings[0].code == "UNREADABLE"
    assert output.entities.emails == ["sender@example.com"]
    assert output.contacts_export[0].email == "sender@example.com"
    assert output.combined_context == "context"
