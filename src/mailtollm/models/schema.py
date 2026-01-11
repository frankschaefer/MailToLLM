from __future__ import annotations

from pydantic import BaseModel, Field


class AttachmentMeta(BaseModel):
    id: str
    filename: str
    path: str
    mime_type: str
    size_bytes: int


class AttachmentContent(BaseModel):
    id: str
    text: str = ""
    tables: list[str] = Field(default_factory=list)
    ocr_text: str = ""


class EmailRecord(BaseModel):
    id: str
    subject: str
    sender: str
    recipients: list[str]
    date: str
    body_text: str
    body_html: str | None = None
    attachments: list[AttachmentMeta] = Field(default_factory=list)

class WarningRecord(BaseModel):
    attachment_id: str
    code: str
    message: str
    details: str | None = None


class EntityIndex(BaseModel):
    emails: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    people: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    addresses: list[str] = Field(default_factory=list)


class ContactExportRecord(BaseModel):
    source: str
    name: str | None = None
    organization: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    notes: str | None = None


class LLMOutput(BaseModel):
    email: EmailRecord
    warnings: list[WarningRecord] = Field(default_factory=list)
    attachment_contents: list[AttachmentContent] = Field(default_factory=list)
    entities: EntityIndex = Field(default_factory=EntityIndex)
    contacts_export: list[ContactExportRecord] = Field(default_factory=list)
    combined_context: str = ""
