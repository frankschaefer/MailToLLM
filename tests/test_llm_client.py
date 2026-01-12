from urllib.error import URLError
from unittest.mock import patch

from mailtollm.services.llm_client import check_llm_available, summarize_text


def test_check_llm_available_failure() -> None:
    with patch("mailtollm.services.llm_client.urlopen", side_effect=URLError("down")):
        ok, detail = check_llm_available("http://localhost:1234/v1/chat/completions")

    assert ok is False
    assert "down" in (detail or "")


def test_summarize_text_unavailable() -> None:
    with patch("mailtollm.services.llm_client.urlopen", side_effect=URLError("down")):
        summary, warning = summarize_text("text", 100)

    assert summary == ""
    assert warning is not None
    assert warning.code == "LLM_UNAVAILABLE"
