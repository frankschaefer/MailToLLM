"""Version information for MailToLLM."""

__version__ = "1.0.1"
__version_date__ = "2026-01-21"

# Version history follows Semantic Versioning (https://semver.org/)
# Format: MAJOR.MINOR.PATCH
#
# MAJOR version: Incompatible API changes
# MINOR version: Add functionality (backwards-compatible)
# PATCH version: Bug fixes (backwards-compatible)
#
# Version History:
# 1.0.1 (2026-01-21) - Bug fixes
#   - Fix organization extraction matching entire email bodies
#   - Increase LLM timeout from 60s to 300s (configurable)
#   - Improve timeout retry detection
#
# 1.0.0 (2026-01-21) - Initial stable release
#   - Real-time contact updates after each email
#   - Auto-close terminal on successful exit
#   - Debug logging for missing contacts
#   - Skip empty calendar entries
#   - Fix NoneType errors in record filtering
#   - Extract names from email addresses
#   - Fix organization extraction (remove titles)
#   - Fix phone number extraction (prevent address false positives)
