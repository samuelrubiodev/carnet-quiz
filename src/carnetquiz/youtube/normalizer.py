from __future__ import annotations

import re
from collections.abc import Iterable

from ..schemas import SegmentInput


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold(), re.UNICODE)


def _strip_progressive(previous: str, current: str) -> str:
    """Remove only exact progressive prefix; preserve independent repeated statements."""
    previous_words, current_words = _words(previous), _words(current)
    if not previous_words or len(current_words) <= len(previous_words):
        return current
    if current_words[: len(previous_words)] == previous_words:
        # Match original words by count, preserving punctuation after new part.
        raw = re.findall(r"\S+", current)
        return " ".join(raw[len(re.findall(r"\S+", previous)) :]).strip() or current
    return current


def normalize_segments(
    segments: Iterable[SegmentInput], min_seconds: float = 1, max_seconds: float = 18
) -> list[SegmentInput]:
    normalized: list[SegmentInput] = []
    for raw in sorted(segments, key=lambda item: item.start_seconds):
        text = re.sub(r"\s+", " ", raw.text).strip()
        if not text:
            continue
        if normalized:
            text = _strip_progressive(normalized[-1].text, text)
        if not text:
            continue
        item = raw.model_copy(update={"text": text})
        previous = normalized[-1] if normalized else None
        if previous and item.end_seconds - previous.start_seconds <= max_seconds and item.start_seconds - previous.end_seconds <= 1 and (previous.end_seconds - previous.start_seconds < min_seconds or len(previous.text) < 28):
            normalized[-1] = previous.model_copy(update={"end_seconds": item.end_seconds, "text": f"{previous.text} {item.text}".strip()})
        else:
            normalized.append(item)
    return normalized
