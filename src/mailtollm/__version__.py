"""Version information for MailToLLM."""

__version__ = "1.0.3"
__version_date__ = "2026-01-23"

# Version history follows Semantic Versioning (https://semver.org/)
# Format: MAJOR.MINOR.PATCH
#
# MAJOR version: Incompatible API changes
# MINOR version: Add functionality (backwards-compatible)
# PATCH version: Bug fixes (backwards-compatible)
#
# Version History:
# 1.0.3 (2026-01-23) - Fix incorrect organization assignment to contacts
#   - Add domain-based organization matching to prevent wrong assignments
#   - Fix: External contacts no longer assigned to wrong companies
#   - Clean prepositional phrases from organization names (e.g., "for", "about")
#   - Remove multi-line job titles from organization extraction
#   - Add support for Swiss/French legal forms: SA, SAS, SARL
#   - Expand title keywords to include full forms (e.g., "Chief Operating Officer")
#   - Add residual title check to prevent incomplete cleanup
#
# 1.0.2 (2026-01-23) - Intelligent token overflow recovery
#   - Add automatic token limit detection from LLM error messages
#   - Implement multi-stage retry strategy (100% → 60% → 40% → 25%)
#   - Add compact prompt mode for later retry attempts
#   - Auto-reprocess records with previous token overflow errors
#   - Add configurable model context window (LLM_MODEL_CONTEXT_TOKENS)
#   - Improve token overflow error detection patterns
#   - Prevent pipeline halt on recoverable token errors
#
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
