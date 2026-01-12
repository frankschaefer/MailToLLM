from urllib.error import URLError
from unittest.mock import patch

import json

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


def test_summarize_text_detail_logging() -> None:
    class DummyResponse:
        def __init__(self, payload: bytes) -> None:
            self._payload = payload
            self.status = 200

        def read(self) -> bytes:
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    payload = json.dumps(
        {
            "choices": [
                {"message": {"content": "short summary"}},
            ]
        }
    ).encode("utf-8")

    logs: list[str] = []

    with patch("mailtollm.services.llm_client.check_llm_available", return_value=(True, None)):
        with patch(
            "mailtollm.services.llm_client.urlopen",
            return_value=DummyResponse(payload),
        ):
            summary, warning = summarize_text(
                "text",
                100,
                on_log=logs.append,
                detail_logging=True,
            )

    assert summary == "short summary"
    assert warning is None
    assert any("LLM request" in entry for entry in logs)
