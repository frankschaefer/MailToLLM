# Project Plan

## Inputs
- Email CSV exports containing message metadata and bodies.
- Attachment folders in a dated folder structure, e.g. `/Users/fs_mku/Desktop/January 6, 2026 03:35 PM`.

## Core stages
1. Ingest CSV: normalize columns, parse dates, and identify attachment references.
2. Resolve attachment paths: map each email to its attachment files on disk.
3. Extract content:
   - PDF: text + tables; if no text, run OCR on rendered pages.
   - PDF with JavaScript-only content or encryption: mark attachment as unreadable.
   - Images: OCR + captions.
   - Office docs (DOCX, PPTX, XLSX): text + tables.
   - Others: filename + metadata.
4. Entity analysis: extract emails, organizations, phone numbers, addresses, and contacts.
5. LLM packaging: generate `combined_context` and structured JSON per email.
6. Output index: maintain a parallel database of extracted entities/contacts for Outlook import.
7. Skip already-processed emails when output exists (id-based).
8. UI-driven batch run with progress and logging.

## Modules
- `io`: CSV reading, attachment discovery, file writing.
- `parsers`: file-type specific extraction.
- `core`: orchestration pipeline + id-based skip logic.
- `ui`: CustomTkinter app.
- `models`: Pydantic schema for outputs.
- `services`: entity extraction, Outlook-ready export, and warnings aggregation.
