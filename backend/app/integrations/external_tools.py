"""External tools — Phase 4 extensions to the ToolRegistry.

These tools are registered into the shared ToolRegistry at startup via
``register_external_tools(registry)``.  Each tool follows the same contract
as the built-in ones: string input → string output, with graceful error
handling so a failing tool never crashes an agent execution.

Available tools
---------------
datetime_now    — Returns current UTC date and time.
random_fact     — Fetches a random interesting fact (uselessfacts.net).
word_count      — Counts words, sentences, and characters in the input text.
json_format     — Pretty-prints JSON input; returns an error on invalid JSON.
url_fetch       — Fetches the text content of a URL (first 2000 chars).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

import httpx

from app.runtime.tools import ToolRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Individual tool implementations
# ---------------------------------------------------------------------------


def _datetime_now(_: str) -> str:
    """Return the current UTC date and time (input is ignored)."""
    now = datetime.now(timezone.utc)
    return now.strftime("Current UTC time: %Y-%m-%d %H:%M:%S UTC (weekday: %A)")


def _random_fact(_: str) -> str:
    """Fetch one random fact from the uselessfacts public API."""
    try:
        with httpx.Client(timeout=8, follow_redirects=True) as client:
            resp = client.get(
                "https://uselessfacts.jsph.pl/api/v2/facts/random",
                params={"language": "en"},
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("text", "[random_fact] No fact returned.")
    except Exception as exc:
        return f"[random_fact] Could not fetch fact: {exc}"


def _word_count(text: str) -> str:
    """Count words, sentences, and characters in the provided text."""
    if not text or not text.strip():
        return "word_count: No text provided."
    words = len(text.split())
    chars = len(text)
    chars_no_spaces = len(text.replace(" ", ""))
    # Rough sentence count: split on .  !  ?
    sentences = len([s for s in re.split(r"[.!?]+", text) if s.strip()])
    return (
        f"Word count: {words} words | "
        f"{sentences} sentence{'s' if sentences != 1 else ''} | "
        f"{chars} chars ({chars_no_spaces} without spaces)"
    )


def _json_format(text: str) -> str:
    """Pretty-print JSON input; returns a parse error on invalid JSON."""
    try:
        parsed = json.loads(text.strip())
        return json.dumps(parsed, indent=2, ensure_ascii=False)
    except json.JSONDecodeError as exc:
        return f"[json_format] Invalid JSON: {exc}"


def _url_fetch(url: str) -> str:
    """Fetch the plain-text body of a URL (first 2000 characters).

    Strips HTML tags so agents receive readable content.
    """
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            resp = client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; YunoAgentBot/1.0)"},
            )
            resp.raise_for_status()
            raw = resp.text

        # Strip HTML tags
        clean = re.sub(r"<[^>]+>", " ", raw)
        # Collapse whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        excerpt = clean[:2000]
        suffix = "..." if len(clean) > 2000 else ""
        return f"[url_fetch] Content from {url}:\n\n{excerpt}{suffix}"
    except Exception as exc:
        return f"[url_fetch] Failed to fetch {url!r}: {exc}"


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------

_EXTRA_TOOLS: dict[str, callable] = {
    "datetime_now": _datetime_now,
    "random_fact": _random_fact,
    "word_count": _word_count,
    "json_format": _json_format,
    "url_fetch": _url_fetch,
}


def register_external_tools(registry: ToolRegistry) -> None:
    """Register all external tools into the provided ToolRegistry.

    Called once at application startup (see main.py lifespan).
    Existing tools (calculator, web_search) are NOT overwritten.
    """
    registered: list[str] = []
    for name, fn in _EXTRA_TOOLS.items():
        if not registry.has_tool(name):
            registry._tools[name] = fn  # noqa: SLF001 — direct insert into internal dict
            registered.append(name)

    if registered:
        logger.info("Registered external tools: %s", ", ".join(registered))
    else:
        logger.debug("No new external tools to register (all already present).")
