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


def test_reject_prepositional_phrase_before_org() -> None:
    """Test that prepositional phrases before organization name are removed.

    Real bug: "the regulatory pathway for Deeplight GmbH" was extracted as organization.
    Expected: "Deeplight GmbH" only.
    """
    text = "We need to discuss the regulatory pathway for Deeplight GmbH before proceeding."
    orgs = _extract_organizations(text)

    # Should extract only "Deeplight GmbH", not the full phrase
    assert "Deeplight GmbH" in orgs
    assert not any("pathway" in org.lower() for org in orgs)
    assert not any("regulatory" in org.lower() for org in orgs)
    assert not any(" for " in org.lower() for org in orgs)
    assert not any("the " in org.lower() for org in orgs)


def test_clean_organization_with_various_prepositions() -> None:
    """Test cleaning organization names with various prepositional phrases."""
    test_cases = [
        ("proposal about Innovation AG", "Innovation AG"),
        ("meeting with TechCorp GmbH", "TechCorp GmbH"),
        ("email from Business Ltd", "Business Ltd"),
        ("presentation to Partners KG", "Partners KG"),
        ("the Startup UG", "Startup UG"),
    ]

    for text, expected in test_cases:
        orgs = _extract_organizations(text)
        assert expected in orgs, f"Expected '{expected}' in {orgs} for text '{text}'"
        # Make sure we got the clean version
        for org in orgs:
            assert "about" not in org.lower()
            assert "with" not in org.lower()
            assert "from" not in org.lower()
            assert " to " not in org.lower()
            assert not org.lower().startswith("the ")


def test_reject_multiline_title_before_org() -> None:
    """Test that job titles on separate lines are removed from organization names.

    Real bug: "Chief Operating Officer\nMenhir Photonics AG" was extracted as organization.
    Expected: "Menhir Photonics AG" only.
    """
    text = """Best regards,
John Doe
Chief Operating Officer
Menhir Photonics AG
Zurich, Switzerland"""
    orgs = _extract_organizations(text)

    # Should extract only "Menhir Photonics AG", not the title
    assert "Menhir Photonics AG" in orgs
    assert not any("Chief Operating Officer" in org for org in orgs)
    assert not any("operating officer" in org.lower() for org in orgs)


def test_reject_full_form_titles() -> None:
    """Test that full-form titles (not just acronyms) are filtered out."""
    test_cases = [
        ("Chief Executive Officer\nTechCorp GmbH", "TechCorp GmbH"),
        ("Chief Technology Officer, Innovation AG", "Innovation AG"),
        ("Chief Financial Officer - Finance Ltd", "Finance Ltd"),
        ("Vice President\nBusiness KG", "Business KG"),
        ("Senior Engineer\nStartup UG", "Startup UG"),
    ]

    for text, expected in test_cases:
        orgs = _extract_organizations(text)
        assert expected in orgs, f"Expected '{expected}' in {orgs} for text '{text}'"
        # Make sure title is not in the extracted organization
        for org in orgs:
            assert "chief" not in org.lower(), f"Title 'chief' found in '{org}'"
            assert "officer" not in org.lower(), f"Title 'officer' found in '{org}'"
            assert "vice president" not in org.lower(), f"Title 'vice president' found in '{org}'"
            assert "senior engineer" not in org.lower(), f"Title 'senior engineer' found in '{org}'"


def test_extract_swiss_french_legal_forms() -> None:
    """Test extraction of Swiss/French legal forms (SA, SAS, SARL)."""
    test_cases = [
        "Deeplight SA is based in Switzerland.",
        "We work with Innovation SAS in France.",
        "Contact Business SARL for details.",
    ]

    orgs = _extract_organizations('\n'.join(test_cases))

    assert "Deeplight SA" in orgs
    assert "Innovation SAS" in orgs
    assert "Business SARL" in orgs


def test_reject_person_name_before_org() -> None:
    """Test that person names before organization are removed from email signatures.

    Real bug: "Natalia Hornes\nDeeplight SA" was extracted as organization.
    Expected: "Deeplight SA" only.
    """
    text = """Best regards

Natalia Hornes
Deeplight SA
Business Operations & Administration
natalia.hornes@deeplight.ai"""
    orgs = _extract_organizations(text)

    # Should extract only "Deeplight SA", not the person name
    assert "Deeplight SA" in orgs
    assert not any("Natalia Hornes" in org for org in orgs)
    assert not any("natalia" in org.lower() for org in orgs)


def test_reject_various_person_names_before_org() -> None:
    """Test that various person name patterns before organizations are filtered."""
    test_cases = [
        ("John Doe\nTechCorp GmbH", "TechCorp GmbH"),
        ("Alice Smith\nInnovation AG", "Innovation AG"),
        ("Bob Johnson Miller\nBusiness Ltd", "Business Ltd"),
        ("Dr. Sarah Williams\nResearch KG", "Research KG"),
    ]

    for text, expected in test_cases:
        orgs = _extract_organizations(text)
        assert expected in orgs, f"Expected '{expected}' in {orgs} for text '{text}'"
        # Make sure person name is not in the extracted organization
        for org in orgs:
            # Extract the person name part (before \n)
            person_name = text.split('\n')[0].strip()
            # Remove title prefixes like "Dr."
            person_name_words = [w for w in person_name.split() if not w.endswith('.')]
            # Check that no part of the person name is in the org
            for word in person_name_words:
                if len(word) > 2:  # Skip very short words like "Dr"
                    assert word not in org, f"Person name word '{word}' found in '{org}'"
