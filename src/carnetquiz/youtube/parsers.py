from __future__ import annotations

import html
import json
import re
from pathlib import Path

from ..schemas import SegmentInput

_TIMESTAMP = re.compile(r"(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2}(?:[.,]\d+)?)")
_TAGS = re.compile(r"<[^>]*>")


def parse_timestamp(value: str) -> float:
    match = _TIMESTAMP.search(value.strip())
    if not match:
        raise ValueError(f"Marca temporal inválida: {value}")
    return int(match["h"]) * 3600 + int(match["m"]) * 60 + float(match["s"].replace(",", "."))


def clean_caption(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub("", value))).strip()


def parse_vtt(content: str, language: str = "es") -> list[SegmentInput]:
    blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n").replace("\r", "\n"))
    segments: list[SegmentInput] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            continue
        start, end = lines[timing_index].split("-->", 1)
        text = clean_caption(" ".join(lines[timing_index + 1 :]))
        if text:
            segments.append(SegmentInput(start_seconds=parse_timestamp(start), end_seconds=parse_timestamp(end), text=text, original_text=text, language=language))
    return segments


def parse_srt(content: str, language: str = "es") -> list[SegmentInput]:
    return parse_vtt(content, language)


def parse_json3(content: str, language: str = "es") -> list[SegmentInput]:
    payload = json.loads(content)
    segments: list[SegmentInput] = []
    for event in payload.get("events", []):
        text = clean_caption("".join(part.get("utf8", "") for part in event.get("segs", [])))
        start = event.get("tStartMs")
        duration = event.get("dDurationMs")
        if text and start is not None and duration:
            segments.append(SegmentInput(start_seconds=start / 1000, end_seconds=(start + duration) / 1000, text=text, original_text=text, language=language))
    return segments


def parse_segmented_text(content: str, language: str = "es") -> list[SegmentInput]:
    """Parse one `start --> end | text` record per line for manual imports."""
    segments: list[SegmentInput] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            continue
        match = re.match(r"\s*(.+?)\s*-->\s*(.+?)\s*\|\s*(.+)\s*$", line)
        if not match:
            raise ValueError(f"Texto segmentado inválido en línea {line_number}")
        text = clean_caption(match.group(3))
        if text:
            segments.append(
                SegmentInput(
                    start_seconds=parse_timestamp(match.group(1)),
                    end_seconds=parse_timestamp(match.group(2)),
                    text=text,
                    original_text=text,
                    language=language,
                )
            )
    return segments


def parse_transcript_file(path: Path, language: str = "es") -> list[SegmentInput]:
    suffix = path.suffix.lower()
    content = path.read_text(encoding="utf-8-sig")
    if suffix == ".vtt":
        return parse_vtt(content, language)
    if suffix == ".srt":
        return parse_srt(content, language)
    if suffix in {".json", ".json3"}:
        return parse_json3(content, language)
    if suffix == ".txt":
        return parse_segmented_text(content, language)
    raise ValueError("Formato admitido: VTT, SRT, JSON3 o texto segmentado")
