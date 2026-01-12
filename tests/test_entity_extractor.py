from mailtollm.services.entity_extractor import extract_entities


def test_extract_entities_basic() -> None:
    text = (
        "ACME GmbH, Mainstrasse 12, 12345 Berlin. "
        "Telefon +49 30 123456, Email: kontakt@acme.de"
    )
    entities = extract_entities(text)

    assert "kontakt@acme.de" in entities.emails
    assert any("GmbH" in org for org in entities.organizations)
    assert any("12345 Berlin" in addr for addr in entities.addresses)
    assert any("+49" in phone for phone in entities.phones)
