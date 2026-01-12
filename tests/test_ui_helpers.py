from mailtollm.ui.app import parse_summary_length


def test_parse_summary_length_empty() -> None:
    assert parse_summary_length("") == 0


def test_parse_summary_length_number() -> None:
    assert parse_summary_length("1500") == 1500


def test_parse_summary_length_invalid() -> None:
    assert parse_summary_length("abc") is None
