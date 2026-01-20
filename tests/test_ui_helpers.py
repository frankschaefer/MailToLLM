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


def test_parse_summary_length_whitespace() -> None:
    """Test that whitespace is properly handled."""
    assert parse_summary_length("  1500  ") == 1500
    assert parse_summary_length("  ") == 0


def test_parse_summary_length_zero() -> None:
    """Test that zero is accepted."""
    assert parse_summary_length("0") == 0


def test_format_duration_large_values() -> None:
    """Test formatting of large durations."""
    assert _format_duration(86400) == "24:00:00"  # 1 day
    assert _format_duration(359999) == "99:59:59"  # 99 hours


def test_format_duration_negative() -> None:
    """Test that negative values are handled as zero."""
    assert _format_duration(-10) == "00:00:00"


def test_estimate_eta_edge_cases() -> None:
    """Test ETA estimation edge cases."""
    # No total records
    assert _estimate_eta(10.0, 5, 0) == "--"

    # Negative remaining (should not happen but handle gracefully)
    assert _estimate_eta(10.0, 15, 10) == "00:00:00"
