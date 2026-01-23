# MailToLLM

**Version: 1.0.2** | **Release Date: 2026-01-23**

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
- `LLM_MODEL_CONTEXT_TOKENS` - Model's total context window in tokens (default: 4096)
- `LLM_TIMEOUT` - Request timeout in seconds (default: 300 = 5 minutes)

### Context Window Management
The system includes intelligent context window management to prevent token overflow errors:

**Automatic Token Limit Detection:**
- When a token overflow error occurs, the system automatically detects the model's context limit
- Extracts the actual token limit from error messages (e.g., "context length of only 4096 tokens")
- Adjusts future retry attempts based on the detected limit

**Multi-Stage Retry Strategy:**
- **Attempt 1**: Uses 100% of configured context (full prompt)
- **Attempt 2**: Reduces to 60% of context if overflow detected
- **Attempt 3**: Reduces to 40% of context + compact prompt (shorter instructions)
- **Attempt 4**: Reduces to 25% of context + compact prompt (last resort)

**Configuration:**
Set `LLM_MODEL_CONTEXT_TOKENS` to match your model's context window:
- 4K models (default): `LLM_MODEL_CONTEXT_TOKENS=4096`
- 8K models: `LLM_MODEL_CONTEXT_TOKENS=8192`
- 16K models: `LLM_MODEL_CONTEXT_TOKENS=16384`
- 32K+ models: `LLM_MODEL_CONTEXT_TOKENS=32768`

The system automatically reserves 25% of the context for prompts and responses, using the remaining 75% for input text.

### Timeout Configuration
If you experience timeout errors during processing:
- **Default timeout**: 300 seconds (5 minutes) per LLM request
- **Increase timeout**: Set `LLM_TIMEOUT` environment variable (in seconds)
  - Example: `export LLM_TIMEOUT=600` for 10 minutes
  - Slow machines or large contexts may need longer timeouts
- **Reduce timeout**: Set lower value if LLM is fast and you want quick failure detection

### Error Recovery
The pipeline includes automatic error recovery for LLM failures:
- **Timeout errors**: Automatically retried up to 2 times (3 total attempts) with 2-second delays
- **Transient errors** (HTTP 500, connection failures): Records are automatically reprocessed on next run
- **Token overflow errors**: Intelligent multi-stage recovery system
  - Automatically detects token/context limit errors during processing
  - System learns the model's actual token limit from error messages
  - Retries up to 4 times with progressively shorter input text (100% → 60% → 40% → 25%)
  - Switches to compact prompts on later attempts to save tokens
  - Records with previous token overflow errors are **automatically reprocessed** on next run
  - Improved detection covers various error patterns: "context overflow", "token limit", "loaded with context length", etc.
- **Critical failures**: After all retries exhausted, pipeline pauses with clear error message and can be resumed

**New in v1.0.2**: Token overflow errors are now fully recoverable. Previously failed records will be automatically reprocessed when you run the pipeline again.

## Contact Management
The pipeline automatically extracts and manages contacts from emails:

### Contact Sources
Contacts are extracted from three sources:
1. **Email sender** - From the "From:" field
2. **Email recipients** - From "To:", "CC:", and "BCC:" fields
3. **Content entities** - Email addresses found in email body and attachments

### Email Address Extraction
The system supports multiple email formats:
- Plain email: `alice@example.com`
- Name with email: `Alice Smith <alice@example.com>`
- Name only (e.g., `John Doe`) - **Not extracted** as it's not a valid email address

**Important**: If your CSV contains only recipient names without email addresses (e.g., "To: John Doe, Jane Smith"), these will NOT be added to the contacts file as they lack email addresses. Ensure your CSV export includes email addresses in the recipient fields.

### Contact Deduplication
- All contacts are stored in a single global `contacts_outlook.csv` file
- Deduplication based on email address (case-insensitive)
- Intelligent merging: when the same email appears multiple times, information is merged (longer names preferred, notes combined, etc.)

### Contact Display
- Real-time contact counter in the UI footer
- Detailed logging showing new contacts, duplicates, and merge information
- Example log messages:
  - `New contact: alice@example.com (Alice Smith) - ACME Corp`
  - `Contact duplicate (no new info): bob@example.com`
  - `Contact updated: carol@example.com - added phone '+49 123', updated name from 'Carol' to 'Carol White'`

### Contact File Updates
- The `contacts_outlook.csv` file is updated **after each processed email**
- This ensures that the contact file is always up-to-date, even during long-running processing sessions
- If you open the file during processing, you'll see the latest contacts immediately

## Versioning

This project follows [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 1.0.0)
- **MAJOR**: Incompatible API changes
- **MINOR**: New features (backwards-compatible)
- **PATCH**: Bug fixes (backwards-compatible)

Version information is displayed:
- In the UI window title: `MailToLLM v1.0.0`
- In the UI header (top-right corner): `v1.0.0` and date
- In the log at pipeline start

See `CHANGELOG.md` for detailed version history and changes.

## Folder notes
- `data/raw` contains CSVs and source folders.
- `data/processed` contains normalized intermediate files.
- `data/output` contains LLM-ready JSON outputs.

See `docs/OUTPUT_SCHEMA.md` for the suggested output structure.
