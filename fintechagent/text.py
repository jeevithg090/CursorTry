"""Pure text helpers used by the conversation loop."""

from __future__ import annotations

import re
from collections.abc import Iterable

# Sarvam's text-to-speech endpoint rejects inputs longer than 500 characters.
TTS_MAX_CHARS = 500

DEFAULT_STOP_WORDS: tuple[str, ...] = ("stop", "close", "bye", "goodbye", "exit", "quit")


def chunk_text(text: str, max_chars: int = TTS_MAX_CHARS) -> list[str]:
    """Split ``text`` into chunks of at most ``max_chars`` characters.

    Splits prefer sentence boundaries, then whitespace, and only cut words that
    are longer than ``max_chars`` on their own. Empty chunks are never returned.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    text = " ".join(text.split())
    chunks: list[str] = []
    while len(text) > max_chars:
        window = text[: max_chars + 1]
        cut = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
        if cut > 0:
            cut += 1  # keep the punctuation
        else:
            cut = window.rfind(" ")
            if cut <= 0:
                cut = max_chars
        chunks.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        chunks.append(text)
    return chunks


def is_stop_request(utterance: str, stop_words: Iterable[str] = DEFAULT_STOP_WORDS) -> bool:
    """Return True if ``utterance`` contains any stop word as a whole word."""
    words = set(re.findall(r"[a-z']+", utterance.casefold()))
    return any(word.casefold() in words for word in stop_words)
