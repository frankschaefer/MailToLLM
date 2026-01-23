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
DEFAULT_MAX_CONTEXT_CHARS = 12000  # ~3000 tokens for input (leaving room for prompt + response)
DEFAULT_MODEL_CONTEXT_TOKENS = 4096  # Default model context window size
DEFAULT_TIMEOUT = 300  # 5 minutes - LLM responses can be slow
DEFAULT_TOKEN_ESTIMATION_RATIO = 4  # Rough estimate: 1 token ≈ 4 chars (for German/English text)
LogCallback = Callable[[str], None]


def get_prompt_for_filetype(file_ext: str, summary_max_chars: int = 1500, compact: bool = False) -> str:
    if compact:
        # Compact version for small context windows
        base_prompt = (
            "Fasse den Inhalt zusammen fuer semantische Suche.\n\n"
            f"Max. {summary_max_chars} Zeichen. Sachlich, praezise.\n"
            "Keine Meta-Kommentare, kein Markdown.\n"
            "Fliesstext mit Fachbegriffen, Zahlen, Namen.\n\n"
            "Am Ende PFLICHT:\n"
            "Schluesselbegriffe: Begriff1, Begriff2, Begriff3\n\n"
            "Auf DEUTSCH."
        )
    else:
        # Full version for normal usage
        base_prompt = (
            "Du bist ein System zur Wissensextraktion fuer semantische Suche (RAG).\n\n"
            "Fasse den folgenden Dateiinhalt so zusammen, dass er fuer spaetere Fragen "
            "maximal gut auffindbar und nutzbar ist.\n\n"
            "REGELN:\n"
            f"- Maximal {summary_max_chars} Zeichen\n"
            "- Sachlich, praezise, ohne Floskeln\n"
            "- Keine Meta-Kommentare (z. B. \"Diese Datei beschreibt...\", "
            "\"Zusammenfassung:\", \"Das Dokument enthaelt...\")\n"
            "- Keine Markdown-Formatierung (**, ##, -, etc.)\n"
            "- Nur reiner Fliesstext ohne Ueberschriften oder Listen\n"
            "- Nutze klare, informationsdichte Saetze\n"
            "- Behalte wichtige Fachbegriffe, Zahlen, Technologien und Personennamen\n"
            "- Beschreibe Zweck, Inhalt, Kontext und Besonderheiten\n"
            "- Falls vorhanden: Ziel, Funktion, Datenarten, Methoden, Abhaengigkeiten\n\n"
            "STRUKTUR (fliessender Text ohne Ueberschriften):\n"
            "- Worum geht es?\n"
            "- Wozu dient es?\n"
            "- Welche Inhalte/Daten/Logik sind enthalten?\n"
            "- Was macht es besonders oder relevant?\n\n"
            "PFLICHTFELD - KEYWORDS (auf neuer Zeile am Ende):\n"
            "Die letzte Zeile MUSS folgendes Format haben:\n"
            "Schluesselbegriffe: Begriff1, Begriff2, Begriff3, Begriff4, Begriff5\n\n"
            "Mindestens 3-8 zentrale Fachbegriffe, Technologien oder Themen als "
            "kommagetrennte Liste.\n"
            "Die Keyword-Zeile MUSS mit \"Schluesselbegriffe:\" beginnen.\n\n"
            "WICHTIG: Antworte AUF DEUTSCH. Beginne direkt mit dem Inhalt, ohne Einleitung."
        )

    type_specific = {
        ".pdf": "Fokus: Dokumenteninhalt, Kernaussagen, Personen und ihre Rollen.",
        ".docx": "Fokus: Dokumenteninhalt, Kernaussagen, Personen und ihre Rollen.",
        ".doc": "Fokus: Dokumenteninhalt, Kernaussagen, Personen und ihre Rollen.",
        ".pptx": "Fokus: Praesentationsthemen, Kernbotschaften, Struktur der Folien.",
        ".ppt": "Fokus: Praesentationsthemen, Kernbotschaften, Struktur der Folien.",
        ".xlsx": "Fokus: Datenarten, Kategorien, Zweck der Tabelle, enthaltene Zahlen.",
        ".xls": "Fokus: Datenarten, Kategorien, Zweck der Tabelle, enthaltene Zahlen.",
        ".xlsm": "Fokus: Datenarten, Kategorien, Makro-Funktionalitaet, Automatisierung.",
        ".xltx": "Fokus: Vorlagenzweck, Struktur, verwendete Kategorien.",
        ".txt": "Fokus: Textinhalt, Zweck, enthaltene Informationen.",
        ".md": "Fokus: Dokumentstruktur, Hauptthemen, technische Details.",
        ".png": "Fokus: Bildinhalte, sichtbarer Text, Diagramme, Personen, Zweck.",
        ".jpg": "Fokus: Bildinhalte, sichtbare Personen, Kontext, Details.",
        ".jpeg": "Fokus: Bildinhalte, sichtbare Personen, Kontext, Details.",
        ".email": "Fokus: E-Mail-Inhalt, Absender, Empfaenger, Termine, Fakten.",
        ".eml": "Fokus: E-Mail-Inhalt, Absender, Empfaenger, Termine, Fakten.",
    }

    normalized = file_ext.lower().strip() if file_ext else ""
    specific = type_specific.get(normalized, "Fokus: Inhalt, Zweck, Relevanz.")
    return f"{base_prompt}\n\n{specific}"


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
    file_ext: str | None = None,
    on_log: LogCallback | None = None,
    detail_logging: bool = False,
) -> tuple[str, WarningRecord | None]:
    if not text.strip():
        return "", None

    url = os.environ.get("LLM_STUDIO_URL", DEFAULT_URL)
    model = os.environ.get("LLM_STUDIO_MODEL", DEFAULT_MODEL)
    max_context_chars = int(os.environ.get("LLM_MAX_CONTEXT_CHARS", str(DEFAULT_MAX_CONTEXT_CHARS)))
    model_context_tokens = int(os.environ.get("LLM_MODEL_CONTEXT_TOKENS", str(DEFAULT_MODEL_CONTEXT_TOKENS)))
    timeout = int(os.environ.get("LLM_TIMEOUT", str(DEFAULT_TIMEOUT)))

    # Calculate safe input size: reserve 25% of context for prompt + response
    safe_input_tokens = int(model_context_tokens * 0.75)
    safe_input_chars = safe_input_tokens * DEFAULT_TOKEN_ESTIMATION_RATIO

    # Use the smaller of user config or calculated safe limit
    max_context_chars = min(max_context_chars, safe_input_chars)

    if detail_logging and on_log:
        on_log(
            f"LLM config: model_context={model_context_tokens} tokens, "
            f"safe_input={safe_input_tokens} tokens ({safe_input_chars} chars), "
            f"max_context={max_context_chars} chars"
        )

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

    # Retry with progressively shorter text on token overflow
    max_retries = 4
    current_max_chars = max_context_chars

    # Reduction factors for each retry attempt (more aggressive progression)
    reduction_factors = [1.0, 0.6, 0.4, 0.25]  # 100%, 60%, 40%, 25% of original

    for attempt in range(max_retries):
        # Apply reduction factor for this attempt
        attempt_max_chars = int(current_max_chars * reduction_factors[attempt])

        # Truncate text if it exceeds max context length
        working_text = text
        original_length = len(text)
        if len(working_text) > attempt_max_chars:
            working_text = working_text[:attempt_max_chars]
            if on_log:
                estimated_tokens = attempt_max_chars // DEFAULT_TOKEN_ESTIMATION_RATIO
                on_log(
                    f"Input text truncated from {original_length} to {attempt_max_chars} chars "
                    f"(~{estimated_tokens} tokens, attempt {attempt + 1}/{max_retries})"
                )

        prompt_start = time.perf_counter()
        # Use compact prompt for later retry attempts to save tokens
        use_compact = attempt >= 2
        prompt = get_prompt_for_filetype(file_ext or ".txt", summary_max_chars=max_chars, compact=use_compact)
        prompt = f"{prompt}\n\nInhalt:\n{working_text}"
        prompt_elapsed = time.perf_counter() - prompt_start
        if detail_logging and on_log:
            on_log(
                f"LLM prompt build: {prompt_elapsed:.2f}s "
                f"(chars={len(prompt)}, type={file_ext or '.txt'}, compact={use_compact})"
            )

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
            with urlopen(request, timeout=timeout) as response:
                raw = response.read()
            request_elapsed = time.perf_counter() - request_start

            parse_start = time.perf_counter()
            data = json.loads(raw.decode("utf-8"))

            # Check for error in response
            if "error" in data:
                error_detail = data.get("error", {})
                error_msg = error_detail.get("message", str(error_detail)) if isinstance(error_detail, dict) else str(error_detail)
                return (
                    "",
                    WarningRecord(
                        attachment_id="",
                        code="LLM_ERROR_RESPONSE",
                        message="LLM returned error",
                        details=error_msg,
                    ),
                )

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

        except HTTPError as exc:
            error_detail = f"HTTP {exc.code}: {exc.reason}"
            error_body_str = ""
            try:
                error_body = exc.read().decode("utf-8")
                error_body_str = error_body
                error_data = json.loads(error_body)
                if "error" in error_data:
                    error_detail = f"{error_detail} - {error_data['error']}"
            except Exception:
                pass

            # Check for context overflow / token limit errors
            is_token_overflow = _is_token_overflow_error(error_detail, error_body_str)

            if is_token_overflow and attempt < max_retries - 1:
                # Try to learn the actual token limit from the error
                detected_limit = _extract_token_limit_from_error(error_detail, error_body_str)
                if detected_limit:
                    # Recalculate safe limit based on detected context size
                    # Reserve 30% for prompt + response
                    new_safe_tokens = int(detected_limit * 0.7)
                    new_safe_chars = new_safe_tokens * DEFAULT_TOKEN_ESTIMATION_RATIO
                    current_max_chars = min(current_max_chars, new_safe_chars)
                    if on_log:
                        on_log(
                            f"Detected model context limit: {detected_limit} tokens. "
                            f"Adjusting to {new_safe_chars} chars (~{new_safe_tokens} tokens)"
                        )

                next_attempt_chars = int(current_max_chars * reduction_factors[attempt + 1])
                estimated_tokens = next_attempt_chars // DEFAULT_TOKEN_ESTIMATION_RATIO
                if on_log:
                    on_log(
                        f"Token overflow detected. Retrying with {next_attempt_chars} chars "
                        f"(~{estimated_tokens} tokens, attempt {attempt + 2}/{max_retries})..."
                    )
                continue

            # Either not a token overflow or we've exhausted retries
            return (
                "",
                WarningRecord(
                    attachment_id="",
                    code="LLM_HTTP_ERROR",
                    message="HTTP Fehler bei LLM Anfrage",
                    details=error_detail,
                ),
            )
        except (URLError, TimeoutError, ConnectionError) as exc:
            return (
                "",
                WarningRecord(
                    attachment_id="",
                    code="LLM_CONNECTION_ERROR",
                    message="Verbindungsfehler zum LLM Studio",
                    details=str(exc),
                ),
            )
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

    # Should not reach here, but just in case
    return (
        "",
        WarningRecord(
            attachment_id="",
            code="LLM_SUMMARY_FAILED",
            message="Zusammenfassung nach mehreren Versuchen fehlgeschlagen",
            details="Token limit could not be satisfied after multiple retries",
        ),
    )


def _extract_content(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    return str(content).strip()


def _is_token_overflow_error(error_detail: str, error_body: str) -> bool:
    """
    Detects if an error is caused by token/context overflow.

    Checks for various patterns in error messages from LLM servers:
    - Context length exceeded
    - Token limit errors
    - Model loaded with smaller context than required
    """
    combined_text = f"{error_detail} {error_body}".lower()

    overflow_indicators = [
        "context length",
        "context_length",
        "token",
        "overflow",
        "loaded with context length",
        "provide a shorter input",
        "maximum context",
        "too long",
        "exceeds",
        "model is loaded with",
        "trying to keep",
        "when context",
    ]

    return any(indicator in combined_text for indicator in overflow_indicators)


def _extract_token_limit_from_error(error_detail: str, error_body: str) -> int | None:
    """
    Tries to extract the actual token limit from error messages.

    Example: "model is loaded with context length of only 4096 tokens"
    Returns: 4096
    """
    import re

    combined_text = f"{error_detail} {error_body}"

    # Pattern: "context length of only X tokens" or "context length of X tokens"
    patterns = [
        r"context length of only (\d+) tokens",
        r"context length of (\d+) tokens",
        r"loaded with context length of (\d+)",
        r"maximum context length is (\d+)",
        r"context window of (\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None


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
