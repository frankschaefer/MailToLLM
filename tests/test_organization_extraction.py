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


def test_reject_long_email_body_text_before_org() -> None:
    """Test that long email body text before GmbH is rejected (real bug example 1)."""
    text = """KORTEQ- internal alignment

Hi Frank,

Since we retook the KORTEQ proposal, we wanted to meet and align together with KIT next tuesday, here is the invite.

Best,
Ignacio


------------------------------------
Ignacio Robles López

Deeplight GmbH"""
    orgs = _extract_organizations(text)

    # Should extract only "Deeplight GmbH", not the entire email body
    assert "Deeplight GmbH" in orgs
    assert not any("KORTEQ" in org and "Deeplight GmbH" in org for org in orgs)
    assert not any("internal alignment" in org.lower() for org in orgs)
    assert not any(len(org) > 60 for org in orgs)  # No suspiciously long org names


def test_reject_email_subject_and_body_before_org() -> None:
    """Test that email subject/body before GmbH is rejected (real bug example 2)."""
    text = """About Invest BW sprint project proposal

Dear everyone,

Please find the draft of the project proposal attached to this email.

Best,
Ignacio

--
Ignacio Robles López

Deeplight GmbH"""
    orgs = _extract_organizations(text)

    # Should extract only "Deeplight GmbH"
    assert "Deeplight GmbH" in orgs
    assert not any("About" in org for org in orgs)
    assert not any("proposal" in org.lower() for org in orgs)


def test_reject_job_title_before_org() -> None:
    """Test that job titles before GmbH are rejected (real bug example 3)."""
    text = "Photonics Design Engineer Position - DLT GmbH"
    orgs = _extract_organizations(text)

    # Should extract "DLT GmbH" only, not the full job title
    # Or skip entirely if it contains "position"
    if orgs:
        assert all("Position" not in org for org in orgs)
        assert all(len(org) < 30 for org in orgs)


def test_extract_valid_short_org_names() -> None:
    """Test that valid short organization names are extracted correctly."""
    text = "Contact Optimus Search GmbH for more information."
    orgs = _extract_organizations(text)
    assert "Optimus Search GmbH" in orgs


def test_extract_org_from_signature() -> None:
    """Test extracting organization from email signature."""
    text = """Best regards,

John Doe
Senior Engineer

Deeplight GmbH
Example Street 123
12345 City"""
    orgs = _extract_organizations(text)
    assert "Deeplight GmbH" in orgs
    # Should not include the job title
    assert not any("Engineer" in org for org in orgs)
