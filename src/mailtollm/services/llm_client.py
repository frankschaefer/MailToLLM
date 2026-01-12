from __future__ import annotations

import json
import os
import time
from typing import Any, Callable
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from mailtollm.models.schema import WarningRecord

DEFAULT_URL = "http://localhost:1234/v1/chat/completions"
DEFAULT_MODEL = "local-model"
LogCallback = Callable[[str], None]


def check_llm_available(url: str) -> tuple[bool, str | None]:
    try:
        models_url = _models_url(url)
        request = Request(models_url, method="GET")
        with urlopen(request, timeout=5) as response:
            if response.status >= 400:
                return False, f"HTTP {response.status}"
        return True, None
    except (HTTPError, URLError, ValueError) as exc:
        return False, str(exc)


def summarize_text(
    text: str,
    max_chars: int,
    on_log: LogCallback | None = None,
    detail_logging: bool = False,
) -> tuple[str, WarningRecord | None]:
    if not text.strip():
        return "", None

    url = os.environ.get("LLM_STUDIO_URL", DEFAULT_URL)
    model = os.environ.get("LLM_STUDIO_MODEL", DEFAULT_MODEL)

    check_start = time.perf_counter()
    available, detail = check_llm_available(url)
    check_elapsed = time.perf_counter() - check_start
    if detail_logging and on_log:
        on_log(f"LLM availability check: {check_elapsed:.2f}s")
    if not available:
        return (
            "",
            WarningRecord(
                attachment_id="",
                code="LLM_UNAVAILABLE",
                message="LLM Studio nicht verfuegbar",
                details=detail,
            ),
        )

    prompt_start = time.perf_counter()
    prompt = (
        "Summarize the following content in German. "
        f"Target length: {max_chars} characters.\n\n"
        f"Content:\n{text}"
    )
    prompt_elapsed = time.perf_counter() - prompt_start
    if detail_logging and on_log:
        on_log(f"LLM prompt build: {prompt_elapsed:.2f}s (chars={len(prompt)})")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a precise summarization assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    try:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        request_start = time.perf_counter()
        with urlopen(request, timeout=60) as response:
            raw = response.read()
        request_elapsed = time.perf_counter() - request_start

        parse_start = time.perf_counter()
        data = json.loads(raw.decode("utf-8"))
        content = _extract_content(data)
        parse_elapsed = time.perf_counter() - parse_start

        if detail_logging and on_log:
            on_log(f"LLM request: {request_elapsed:.2f}s (bytes={len(raw)})")
            on_log(f"LLM response parse: {parse_elapsed:.2f}s (chars={len(content)})")
        if max_chars > 0 and len(content) > max_chars:
            content = content[:max_chars].rstrip()
            if detail_logging and on_log:
                on_log(f"LLM summary truncated to {max_chars} chars")
        return content, None
    except Exception as exc:
        return (
            "",
            WarningRecord(
                attachment_id="",
                code="LLM_SUMMARY_FAILED",
                message="Zusammenfassung fehlgeschlagen",
                details=str(exc),
            ),
        )


def _extract_content(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    return str(content).strip()


def _models_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if path.endswith("/chat/completions"):
        path = path[: -len("/chat/completions")] + "/models"
    elif path.endswith("/v1"):
        path = path + "/models"
    elif not path.endswith("/models"):
        path = path + "/models"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))
