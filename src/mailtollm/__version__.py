"""Version information for MailToLLM."""

__version__ = "1.0.7"
__version_date__ = "2026-01-23"

# Version history follows Semantic Versioning (https://semver.org/)
# Format: MAJOR.MINOR.PATCH
#
# MAJOR version: Incompatible API changes
# MINOR version: Add functionality (backwards-compatible)
# PATCH version: Bug fixes (backwards-compatible)
#
# Version History:
# 1.0.7 (2026-01-23) - Add application launcher and comprehensive start guide
#   - Add run.py launcher script for easy app startup without installation
#   - Add START.md with multiple startup methods and troubleshooting
#   - Document icon usage and standalone app creation with PyInstaller
#
# 1.0.6 (2026-01-23) - Add macOS application icon and clean up documentation
#   - Add custom icon for macOS application (envelope with AI theme)
#   - Implement window icon display in CustomTkinter app
#   - Add icon generation script for future updates
#   - Replace remaining real company names in code comments
#   - Configure hatchling to include icon resources in package
#
# 1.0.5 (2026-01-23) - Replace real company and person names with fictional examples
#   - Replace all real company names in tests and documentation with fictional names
#   - Replace all real person names and email addresses with fictional examples
#   - Improve code privacy and generalization
#   - No functional changes, only documentation and test data updates
#
# 1.0.4 (2026-01-23) - Fix person names in organization extraction
#   - Remove person names before organization in email signatures
#   - Fix: "Person Name\nCompany SA" now correctly extracts as "Company SA"
#   - Add detection for capitalized person names (2-4 words without legal suffix)
#   - Improve signature parsing to separate names from company names
#
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
