# Changelog

All notable changes to MailToLLM will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-01-21

### Fixed
- Organization extraction now limits to 2-5 words before legal suffix (prevents matching entire email bodies)
- Organization extraction filters out false positives: job titles, email subjects, greetings, proposals
- Organization extraction skips suspiciously long matches (>60 characters)
- LLM timeout increased from 60 seconds to 300 seconds (5 minutes) to prevent frequent timeouts
- Timeout retry detection improved to handle URLError and various timeout error formats

### Added
- `LLM_TIMEOUT` environment variable for configurable timeout (default: 300 seconds)
- Comprehensive tests for organization extraction edge cases
- Debug logging for retry decisions (shows why retries succeed or fail)

### Changed
- Default LLM request timeout: 60s → 300s
- Organization regex now more restrictive to prevent false positives

## [1.0.0] - 2026-01-21

### Added
- Professional version display in UI header (top-right corner)
- Version logging at pipeline start
- Semantic versioning system with `__version__.py`
- Real-time contact file updates after each processed email
- Auto-close terminal window on successful app exit
- Debug logging for missing contact extraction
- Skip logic for empty calendar entries without contacts/attachments/content
- Name extraction from email addresses (e.g., john.doe@example.com → "John Doe")
- Phone number validation to prevent address component false positives
- Email and attachment counters in UI footer
- Comprehensive test suite for entity extraction

### Changed
- Organization extraction now filters out titles (e.g., "CEO, Company GmbH" → "Company GmbH")
- Phone number extraction uses multiple specific patterns instead of single broad regex
- Contact file (`contacts_outlook.csv`) updates incrementally for better progress visibility

### Fixed
- NoneType AttributeError in record processing filter when CSV contains None values
- Phone number false positives from addresses (e.g., "44\n8002" from "Stockerstrasse 44, 8002 Zurich")
- Empty Full Name fields for contacts - now extracts from email addresses if not in "Name <email>" format
- Date formats incorrectly recognized as phone numbers (e.g., "07.01.2026")
- Organization field containing person titles instead of just company names

### Technical Details
- Version: 1.0.0
- Release Date: 2026-01-21
- Python: 3.10+
- UI Framework: CustomTkinter
- Validation: Pydantic models

---

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):

**MAJOR.MINOR.PATCH**

- **MAJOR**: Incompatible API changes
- **MINOR**: Add functionality (backwards-compatible)
- **PATCH**: Bug fixes (backwards-compatible)

Examples:
- `1.0.0` → `2.0.0`: Breaking changes
- `1.0.0` → `1.1.0`: New features
- `1.0.0` → `1.0.1`: Bug fixes
