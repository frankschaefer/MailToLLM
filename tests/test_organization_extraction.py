"""Tests for organization extraction with title filtering."""
from mailtollm.services.entity_extractor import _extract_organizations


def test_extract_simple_organization() -> None:
    """Test extracting simple organization names."""
    text = "I work at Deeplight GmbH in Berlin."
    orgs = _extract_organizations(text)
    assert "Deeplight GmbH" in orgs


def test_extract_organization_removes_ceo_title() -> None:
    """Test that CEO title is removed from organization name."""
    text = "Contact CEO, Deeplight GmbH for more information."
    orgs = _extract_organizations(text)
    assert "Deeplight GmbH" in orgs
    assert "CEO, Deeplight GmbH" not in orgs


def test_extract_organization_removes_various_titles() -> None:
    """Test that various titles are removed."""
    test_cases = [
        ("CTO, TechCorp GmbH", "TechCorp GmbH"),
        ("CFO, Finance AG", "Finance AG"),
        ("Director, Management LLC", "Management LLC"),
        ("Manager, Business UG", "Business UG"),
        ("President, Global Inc", "Global Inc"),
        ("Founder, Startup GmbH", "Startup GmbH"),
    ]

    for text, expected_org in test_cases:
        orgs = _extract_organizations(text)
        assert expected_org in orgs, f"Expected '{expected_org}' in {orgs} for text '{text}'"
        assert text not in orgs, f"Should not include full text '{text}' in {orgs}"


def test_extract_organization_with_dash_separator() -> None:
    """Test that titles with dash separator are handled."""
    text = "CEO - Deeplight GmbH"
    orgs = _extract_organizations(text)
    assert "Deeplight GmbH" in orgs


def test_extract_organization_without_title() -> None:
    """Test that organizations without titles are extracted normally."""
    text = "Deeplight GmbH is a software company."
    orgs = _extract_organizations(text)
    assert "Deeplight GmbH" in orgs


def test_extract_multiple_organizations() -> None:
    """Test extracting multiple organizations from text."""
    text = "Partnership between Deeplight GmbH and TechCorp AG."
    orgs = _extract_organizations(text)
    assert "Deeplight GmbH" in orgs
    assert "TechCorp AG" in orgs


def test_extract_organization_preserves_complex_names() -> None:
    """Test that complex organization names are preserved."""
    text = "Smith & Partners GmbH is our legal advisor."
    orgs = _extract_organizations(text)
    assert "Smith & Partners GmbH" in orgs
