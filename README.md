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

## Folder notes
- `data/raw` contains CSVs and source folders.
- `data/processed` contains normalized intermediate files.
- `data/output` contains LLM-ready JSON outputs.

See `docs/OUTPUT_SCHEMA.md` for the suggested output structure.
