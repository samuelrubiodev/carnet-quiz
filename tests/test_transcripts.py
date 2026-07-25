from carnetquiz.schemas import SegmentInput
from carnetquiz.services.jobs import parse_duration
from carnetquiz.youtube.normalizer import normalize_segments
from carnetquiz.youtube.parsers import parse_segmented_text, parse_srt, parse_vtt


def test_parse_durations():
    assert parse_duration("30m") == 1800
    assert parse_duration("01:30:00") == 5400
    assert parse_duration("90") == 90


def test_parse_vtt_and_srt():
    text = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHola <b>mundo</b>\n"
    assert parse_vtt(text)[0].text == "Hola mundo"
    assert parse_srt("1\n00:00:01,000 --> 00:00:03,000\nHola\n")[0].start_seconds == 1
    assert parse_segmented_text("00:00:03 --> 00:00:04 | Manual")[0].text == "Manual"


def test_normalizes_progressive_captions():
    values = [
        SegmentInput(start_seconds=0, end_seconds=0.5, text="La velocidad máxima"),
        SegmentInput(start_seconds=0.5, end_seconds=3, text="La velocidad máxima es 50 km/h"),
    ]
    result = normalize_segments(values)
    assert len(result) == 1
    assert result[0].text == "La velocidad máxima es 50 km/h"
