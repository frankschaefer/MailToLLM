# MailToLLM

Python UI app (CustomTkinter) for reading email CSV files and their attachments, then producing LLM-ready structured outputs.

## Goals
- Ingest CSV exports of emails and locate their attachments on disk.
- Extract text and metadata from common attachment types (PDF, images, PPTX, DOCX, XLSX, etc.).
- Output a consistent, LLM-friendly JSON package that preserves context and relationships.

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m mailtollm.ui.app
```

## OCR setup
For OCR on images and scanned PDFs, install Tesseract on your system and ensure it is on PATH.
The Python dependency `pytesseract` is included in the project dependencies.

## LLM summary (LM Studio)
By default, summaries are sent to `http://localhost:1234/v1/chat/completions` using the model
name `local-model`. Override via environment variables:
- `LLM_STUDIO_URL` - The URL of your LLM Studio API endpoint
- `LLM_STUDIO_MODEL` - The model name to use
- `LLM_MAX_CONTEXT_CHARS` - Maximum characters for input text (default: 12000, ~3000 tokens)

### Context Window Management
To prevent "context overflow" errors when the model's context window is too small:
- Input text is automatically truncated to fit within `LLM_MAX_CONTEXT_CHARS`
- Default is set to 12,000 characters (~3,000 tokens) to work with 4K context models
- Adjust `LLM_MAX_CONTEXT_CHARS` based on your model's context length:
  - 4K context models: use 12000 (default)
  - 8K context models: use 28000
  - 16K context models: use 60000
  - 32K+ context models: use 120000 or higher

### Error Recovery
The pipeline includes automatic error recovery for LLM failures:
- **Transient errors** (HTTP 500, connection failures): Records are automatically reprocessed on next run
- **Context overflow errors**: Not reprocessed (would fail again); increase context limit or truncation is applied
- **Critical failures**: Pipeline pauses with clear error message, can be resumed after fixing the issue

## Folder notes
- `data/raw` contains CSVs and source folders.
- `data/processed` contains normalized intermediate files.
- `data/output` contains LLM-ready JSON outputs.

See `docs/OUTPUT_SCHEMA.md` for the suggested output structure.
