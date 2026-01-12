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


def get_prompt_for_filetype(file_ext: str, summary_max_chars: int = 1500) -> str:
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
    prompt = get_prompt_for_filetype(file_ext or ".txt", summary_max_chars=max_chars)
    prompt = f"{prompt}\n\nInhalt:\n{text}"
    prompt_elapsed = time.perf_counter() - prompt_start
    if detail_logging and on_log:
        on_log(
            f"LLM prompt build: {prompt_elapsed:.2f}s "
            f"(chars={len(prompt)}, type={file_ext or '.txt'})"
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
