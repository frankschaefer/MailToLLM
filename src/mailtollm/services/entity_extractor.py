from __future__ import annotations

import re

from mailtollm.models.schema import EntityIndex

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")

ORG_SUFFIXES = ["gmbh", "ag", "inc", "llc", "ltd", "kg", "gbr", "ug", "plc"]


def extract_entities(text: str) -> EntityIndex:
    emails = sorted(set(EMAIL_RE.findall(text)))
    phones = sorted(set(PHONE_RE.findall(text)))
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
