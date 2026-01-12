from mailtollm.ui.app import _estimate_eta, _format_duration, parse_summary_length


def test_parse_summary_length_empty() -> None:
    assert parse_summary_length("") == 0


def test_parse_summary_length_number() -> None:
    assert parse_summary_length("1500") == 1500


def test_parse_summary_length_invalid() -> None:
    assert parse_summary_length("abc") is None


def test_format_duration() -> None:
    assert _format_duration(0) == "00:00:00"
    assert _format_duration(3661) == "01:01:01"


def test_estimate_eta() -> None:
    assert _estimate_eta(10.0, 0, 100) == "calculating"
    assert _estimate_eta(10.0, 10, 10) == "00:00:00"
    assert _estimate_eta(10.0, 10, 20) == "00:00:10"
