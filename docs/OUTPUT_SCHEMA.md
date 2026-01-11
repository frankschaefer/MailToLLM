# Suggested Output Structure (LLM-ready)

Produce one JSON per email. Keep all fields explicit and normalized to ease LLM parsing.

```json
{
  "email": {
    "id": "string",
    "subject": "string",
    "sender": "string",
    "recipients": ["string"],
    "date": "ISO-8601",
    "body_text": "string",
    "body_html": "string or null",
    "attachments": [
      {
        "id": "string",
        "filename": "string",
        "path": "string",
        "mime_type": "string",
        "size_bytes": 12345
      }
    ]
  },
  "warnings": [
    {
      "attachment_id": "string",
      "code": "UNREADABLE",
      "message": "Nicht lesbar",
      "details": "string"
    }
  ],
  "attachment_contents": [
    {
      "id": "string",
      "text": "extracted text",
      "tables": ["table serialized as TSV or Markdown"],
      "ocr_text": "string"
    }
  ],
  "entities": {
    "emails": ["string"],
    "organizations": ["string"],
    "people": ["string"],
    "phones": ["string"],
    "addresses": ["string"]
  },
  "contacts_export": [
    {
      "source": "email",
      "name": "string",
      "organization": "string",
      "email": "string",
      "phone": "string",
      "address": "string",
      "notes": "string"
    }
  ],
  "combined_context": "LLM prompt-ready blend of email + attachment content"
}
```

## Combined context
Recommended structure:
- Email header summary (from/to/date/subject)
- Email body (clean text, paragraphs)
- Attachment sections: filename, type, extracted text, tables, OCR

## File naming
`{email_id}.json` stored in `data/output/`.

## Outlook-friendly export
Contacts can also be emitted as CSV with headers compatible with Outlook import,
e.g. `Full Name`, `Company`, `Email Address`, `Business Phone`, `Business Address`, `Notes`.
