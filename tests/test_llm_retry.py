"""Tests for LLM timeout retry logic."""
from __future__ import annotations

from mailtollm.core.pipeline import _is_timeout_error, LLMConnectionError


def test_is_timeout_error_detects_timeout() -> None:
    """Test that timeout errors are correctly identified."""
    exc = LLMConnectionError("LLM connection lost: timed out")
    assert _is_timeout_error(exc) is True


def test_is_timeout_error_detects_timeout_alternative() -> None:
    """Test alternative timeout message format."""
    exc = LLMConnectionError("Connection timeout occurred")
    assert _is_timeout_error(exc) is True


def test_is_timeout_error_rejects_non_timeout() -> None:
    """Test that non-timeout errors are not identified as timeout."""
    exc = LLMConnectionError("Connection refused")
    assert _is_timeout_error(exc) is False

    exc2 = LLMConnectionError("HTTP Error 500")
    assert _is_timeout_error(exc2) is False


def test_is_timeout_error_case_insensitive() -> None:
    """Test that timeout detection is case-insensitive."""
    exc = LLMConnectionError("TIMED OUT")
    assert _is_timeout_error(exc) is True

    exc2 = LLMConnectionError("Timeout")
    assert _is_timeout_error(exc2) is True
