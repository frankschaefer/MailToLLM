from __future__ import annotations

import re

from mailtollm.models.schema import EntityIndex

# Email regex - basic pattern
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)

# Phone regex - more restrictive pattern for actual phone numbers
# Matches international format (+XX), country code (00XX), or local with area code
# Requires: 8-15 digits total, no newlines, limited separators
PHONE_PATTERNS = [
    # International format: +41 44 123 45 67, +1-555-123-4567
    re.compile(r"\+\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,4}[\s.-]?\d{1,4}"),
    # Country code format: 0041 44 123 45 67
    re.compile(r"00\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,4}[\s.-]?\d{1,4}"),
    # Local with area code: (044) 123 45 67, 044-1234567, 044/123 45 67
    re.compile(r"\(?\d{2,5}\)?[\s./-]\d{3,4}[\s./-]?\d{2,4}[\s./-]?\d{0,4}"),
]

# Date patterns to exclude from phone numbers
DATE_PATTERNS = [
    re.compile(r"\d{1,2}\.\d{1,2}\.\d{2,4}"),  # DD.MM.YYYY or DD.MM.YY
    re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}"),    # DD/MM/YYYY
    re.compile(r"\d{2,4}-\d{1,2}-\d{1,2}"),     # YYYY-MM-DD
]

ORG_SUFFIXES = ["gmbh", "ag", "inc", "llc", "ltd", "kg", "gbr", "ug", "plc", "sa", "sas", "sarl"]


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
    - Address components (street numbers, postal codes)
    - Strings with too few or too many digits
    - Strings with newlines (street addresses split across lines)
    """
    phone = phone.strip()

    # Reject if contains newline (address split across lines)
    if '\n' in phone or '\r' in phone:
        return False

    # Check if it matches any date pattern
    for date_pattern in DATE_PATTERNS:
        if date_pattern.fullmatch(phone):
            return False

    # Count digits only
    digit_count = sum(c.isdigit() for c in phone)

    # Phone numbers typically have 8-15 digits (international standard)
    # Too few: likely partial number or address component
    # Too many: likely multiple numbers or other data
    if digit_count < 8 or digit_count > 15:
        return False

    # Must not be mostly dots/slashes (date-like)
    separator_count = phone.count('.') + phone.count('/') + phone.count('-')
    if separator_count > 3:  # More than 3 separators is unusual for phone numbers
        return False

    # Reject if looks like postal code + house number pattern
    # Example: "8002 44" or "44 8002" (4-5 digits, space, 2-3 digits)
    if re.match(r'^\d{2,3}\s+\d{4,5}$', phone) or re.match(r'^\d{4,5}\s+\d{2,3}$', phone):
        return False

    return True


def _extract_and_validate_phones(text: str) -> list[str]:
    """Extract and validate phone numbers from text.

    Uses multiple regex patterns to match different phone number formats.
    """
    raw_phones: list[str] = []

    # Try all phone patterns
    for pattern in PHONE_PATTERNS:
        raw_phones.extend(pattern.findall(text))

    # Validate and deduplicate
    valid_phones = [phone for phone in raw_phones if _is_valid_phone(phone)]
    return sorted(set(valid_phones))


def _clean_organization_name(org: str) -> str:
    """Clean organization name by removing prepositional phrases and keeping only the core name.

    Examples:
    - "the regulatory pathway for Deeplight GmbH" -> "Deeplight GmbH"
    - "Proposal About Innovation AG" -> "Innovation AG"
    - "Deeplight GmbH" -> "Deeplight GmbH" (unchanged)

    Returns empty string if no valid organization name can be extracted.
    """
    if not org:
        return ""

    # Split by common prepositions and take the last part (usually contains the actual org name)
    prepositions = [' for ', ' about ', ' at ', ' with ', ' from ', ' to ']
    for prep in prepositions:
        if prep in org.lower():
            # Take the part after the last preposition
            parts = re.split(prep, org, flags=re.IGNORECASE)
            org = parts[-1].strip()

    # Remove leading articles (the, a, an)
    org = re.sub(r'^\s*(the|a|an)\s+', '', org, flags=re.IGNORECASE)

    # Extract the core organization name: look for pattern of 1-5 capitalized words + legal suffix
    # This removes any remaining junk before the actual company name
    for suffix in ORG_SUFFIXES:
        # Match the last occurrence of "CapitalizedWords + Suffix" in the string
        pattern = re.compile(
            rf'\b([A-Z][\w&]*(?:\s+(?:&\s+)?[A-Z][\w&]*){0,4})\s+{suffix}\b',
            re.IGNORECASE
        )
        matches = list(pattern.finditer(org))
        if matches:
            # Take the last match (most likely to be the actual org name)
            return matches[-1].group(0).strip()

    return org.strip()


def _extract_organizations(text: str) -> list[str]:
    """Extract organization names from text.

    Filters out common patterns that are not organizations:
    - Limits to 2-5 words before legal suffix (prevents matching long text)
    - Removes titles/positions before organization (e.g., "CEO, Deeplight GmbH" -> "Deeplight GmbH")
    - Filters out common false positives (job titles, email subjects)
    """
    matches: set[str] = set()
    for suffix in ORG_SUFFIXES:
        # Match 1-5 capitalized words before the legal suffix
        # This prevents matching entire paragraphs
        pattern = re.compile(
            rf"\b([A-Z][\w&]*(?:\s+(?:&\s+)?[A-Z][\w&]*){'{0,4}'})\s+{suffix}\b",
            re.IGNORECASE
        )
        for match in pattern.finditer(text):
            org = match.group(0).strip()

            # Skip if organization name is suspiciously long (>60 chars = likely not a company name)
            if len(org) > 60:
                continue

            # Skip common false positive patterns
            org_lower = org.lower()
            false_positive_keywords = [
                'position',      # "Engineer Position - Company GmbH"
                'about',         # "About Project - Company GmbH"
                'subject:',      # Email subject lines
                'hi ',           # Email greetings
                'dear ',         # Email greetings
                'best,',         # Email closings
                'regards,',      # Email closings
                'proposal',      # "Project Proposal - Company GmbH"
                'alignment',     # "Internal Alignment - Company GmbH"
                'pathway',       # "regulatory pathway for Company GmbH"
                ' for ',         # "... for Company GmbH"
                ' the ',         # "... the Company GmbH"
            ]
            if any(keyword in org_lower for keyword in false_positive_keywords):
                continue

            # Remove common title/position prefixes (e.g., "CEO, Company" -> "Company")
            # Also remove person names before organization (e.g., "John Doe\nCompany SA" -> "Company SA")
            # Look for pattern: "Title, Organization" or "Title - Organization" or "Title\nOrganization"
            # Split by comma, dash, or newline
            if ',' in org or ' - ' in org or '\n' in org:
                # Split by comma, dash, or newline
                parts = re.split(r'[,\n-]\s*', org)
                # Check if first part looks like a title (short, no legal suffix)
                if len(parts) > 1:
                    first_part = parts[0].lower().strip()
                    first_part_orig = parts[0].strip()

                    # Common titles to skip (including full forms like "chief operating officer")
                    title_keywords = [
                        'ceo', 'cto', 'cfo', 'coo',  # Acronyms
                        'chief executive officer', 'chief technology officer',
                        'chief financial officer', 'chief operating officer',
                        'director', 'manager', 'president', 'vice president',
                        'founder', 'co-founder', 'owner', 'partner',
                        'lead', 'head', 'engineer', 'senior', 'principal',
                        'consultant', 'specialist', 'coordinator'
                    ]

                    # Check if first part is a title or contains title keywords
                    is_title = any(keyword in first_part for keyword in title_keywords)

                    # Check if first part looks like a person name (2-3 capitalized words, no legal suffix)
                    # Example: "Alice Manager" or "John Doe Smith"
                    is_person_name = (
                        not is_title and
                        not any(first_part.endswith(suf.lower()) for suf in ORG_SUFFIXES) and
                        len(first_part_orig.split()) <= 4 and  # Max 4 words
                        all(word[0].isupper() for word in first_part_orig.split() if word)  # All words capitalized
                    )

                    if is_title or is_person_name:
                        # Use the part after the separator (skip the title/name)
                        remaining_parts = [p.strip() for p in parts[1:] if p.strip()]
                        if remaining_parts:
                            org = ' '.join(remaining_parts).strip()

            # Clean up organization name by extracting just the company name + suffix
            # This removes prepositional phrases like "the regulatory pathway for Deeplight GmbH"
            org = _clean_organization_name(org)
            if not org:
                continue

            # Final validation: must contain the legal suffix
            if not any(org.lower().endswith(suf.lower()) for suf in ORG_SUFFIXES):
                continue

            # Skip if still contains job title keywords (failed to clean properly)
            org_check = org.lower()
            residual_titles = ['chief operating officer', 'chief executive', 'chief technology',
                              'chief financial', 'vice president', 'senior engineer']
            if any(title in org_check for title in residual_titles):
                continue

            matches.add(org)

    return sorted(matches)


def _extract_addresses(text: str) -> list[str]:
    pattern = re.compile(
        r"\b([A-Z][a-zA-Z]+\s+\d+[a-zA-Z]?\,?\s+\d{4,5}\s+[A-Za-z\s]+)\b"
    )
    return sorted(set(m.group(1).strip() for m in pattern.finditer(text)))
