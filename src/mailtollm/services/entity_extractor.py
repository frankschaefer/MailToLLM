from __future__ import annotations

import re

from mailtollm.models.schema import EntityIndex

# Email regex - basic pattern
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)

# Phone regex - must start with + or digit, contain enough digits
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")

# Date patterns to exclude from phone numbers
DATE_PATTERNS = [
    re.compile(r"\d{1,2}\.\d{1,2}\.\d{2,4}"),  # DD.MM.YYYY or DD.MM.YY
    re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}"),    # DD/MM/YYYY
    re.compile(r"\d{2,4}-\d{1,2}-\d{1,2}"),     # YYYY-MM-DD
]

ORG_SUFFIXES = ["gmbh", "ag", "inc", "llc", "ltd", "kg", "gbr", "ug", "plc"]


def extract_entities(text: str) -> EntityIndex:
    emails = _extract_and_validate_emails(text)
    phones = _extract_and_validate_phones(text)
    organizations = _extract_organizations(text)
    addresses = _extract_addresses(text)
    people = []
    return EntityIndex(
        emails=emails,
        organizations=organizations,
        people=people,
        phones=phones,
        addresses=addresses,
    )


def _is_valid_email(email: str) -> bool:
    """Validate that an email address is legitimate.

    Filters out:
    - Embedded image references (e.g., image001.jpg@01DC742F.BBA)
    - Invalid TLDs
    - Suspicious patterns
    """
    email = email.lower()

    # Check for image file extensions before @
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff']
    local_part = email.split('@')[0]
    if any(local_part.endswith(ext) for ext in image_extensions):
        return False

    # Check for suspicious hex-like domains (e.g., @01DC742F.BBA)
    domain = email.split('@')[1] if '@' in email else ''
    if domain and re.match(r'^[0-9A-F]+\.[A-Z]+$', domain, re.IGNORECASE):
        return False

    # Domain must have at least one dot and valid TLD
    if '.' not in domain:
        return False

    # TLD should be 2-6 letters (not numbers)
    tld = domain.split('.')[-1]
    if not (2 <= len(tld) <= 6 and tld.isalpha()):
        return False

    return True


def _extract_and_validate_emails(text: str) -> list[str]:
    """Extract and validate email addresses from text."""
    raw_emails = EMAIL_RE.findall(text)
    valid_emails = [email for email in raw_emails if _is_valid_email(email)]
    return sorted(set(valid_emails))


def _is_valid_phone(phone: str) -> bool:
    """Validate that a phone number is legitimate.

    Filters out:
    - Date formats (DD.MM.YYYY, DD/MM/YYYY, etc.)
    - Strings with too few digits
    """
    # Check if it matches any date pattern
    for date_pattern in DATE_PATTERNS:
        if date_pattern.fullmatch(phone.strip()):
            return False

    # Must contain at least 6 digits (minimum valid phone number)
    digit_count = sum(c.isdigit() for c in phone)
    if digit_count < 6:
        return False

    # Must not be mostly dots/slashes (date-like)
    separator_count = phone.count('.') + phone.count('/') + phone.count('-')
    if separator_count > 2:  # More than 2 separators suggests date format
        return False

    return True


def _extract_and_validate_phones(text: str) -> list[str]:
    """Extract and validate phone numbers from text."""
    raw_phones = PHONE_RE.findall(text)
    valid_phones = [phone for phone in raw_phones if _is_valid_phone(phone)]
    return sorted(set(valid_phones))


def _extract_organizations(text: str) -> list[str]:
    matches: set[str] = set()
    for suffix in ORG_SUFFIXES:
        pattern = re.compile(rf"\b([A-Z][\w&.,\s-]+\s{suffix})\b", re.IGNORECASE)
        matches.update(m.group(1).strip() for m in pattern.finditer(text))
    return sorted(matches)


def _extract_addresses(text: str) -> list[str]:
    pattern = re.compile(
        r"\b([A-Z][a-zA-Z]+\s+\d+[a-zA-Z]?\,?\s+\d{4,5}\s+[A-Za-z\s]+)\b"
    )
    return sorted(set(m.group(1).strip() for m in pattern.finditer(text)))
