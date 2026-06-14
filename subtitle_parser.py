"""Parse subtitle files (SRT, VTT, TXT) into segments + full_text."""

import re
import logging

logger = logging.getLogger(__name__)

# Matches timestamps like: 00:00:01,000 --> 00:00:05,000  (SRT)
# or: 00:00:01.000 --> 00:00:05.000  (VTT)
_TIMESTAMP_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)


def _timestamp_to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(text: str) -> dict:
    """Parse SRT-format subtitle text.

    Returns {"segments": [...], "full_text": "..."} like the transcriber.
    """
    segments = []
    # Split on blank lines (separate subtitle blocks)
    blocks = re.split(r"\n\s*\n", text.strip())

    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue

        # Find the timestamp line
        ts_match = None
        text_lines = []
        for line in lines:
            m = _TIMESTAMP_RE.match(line.strip())
            if m:
                ts_match = m
            elif ts_match is not None:
                # After timestamp, everything is subtitle text
                text_lines.append(line.strip())
            # Skip index numbers (lines before timestamp that are just digits)

        if ts_match and text_lines:
            start = _timestamp_to_seconds(
                ts_match.group(1), ts_match.group(2),
                ts_match.group(3), ts_match.group(4),
            )
            end = _timestamp_to_seconds(
                ts_match.group(5), ts_match.group(6),
                ts_match.group(7), ts_match.group(8),
            )
            text = " ".join(text_lines)
            segments.append({
                "start": round(start, 2),
                "end": round(end, 2),
                "text": text,
            })

    full_text = " ".join(s["text"] for s in segments)
    return {"segments": segments, "full_text": full_text}


def parse_vtt(text: str) -> dict:
    """Parse WebVTT-format subtitle text.

    Returns {"segments": [...], "full_text": "..."} like the transcriber.
    """
    segments = []
    # Remove WEBVTT header
    if text.startswith("WEBVTT"):
        text = text[6:]
    # Remove optional header lines (lines before first blank line)
    m = re.search(r"\n\s*\n", text)
    if m:
        text = text[m.start():]
    text = text.strip()

    # Split on blank lines
    blocks = re.split(r"\n\s*\n", text)

    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue

        # First line should be timestamp (possibly with optional cue id before)
        ts_match = None
        text_start = 0
        for i, line in enumerate(lines):
            m = _TIMESTAMP_RE.match(line.strip())
            if m:
                ts_match = m
                text_start = i + 1
                break

        if ts_match:
            start = _timestamp_to_seconds(
                ts_match.group(1), ts_match.group(2),
                ts_match.group(3), ts_match.group(4),
            )
            end = _timestamp_to_seconds(
                ts_match.group(5), ts_match.group(6),
                ts_match.group(7), ts_match.group(8),
            )
            # Collect text lines, strip VTT inline tags
            text_lines = []
            for line in lines[text_start:]:
                line = line.strip()
                if line:
                    # Remove VTT tags like <c>, <v>, </c>, etc.
                    line = re.sub(r"<[^>]+>", "", line)
                    text_lines.append(line)
            text_content = " ".join(text_lines)
            if text_content:
                segments.append({
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "text": text_content,
                })

    full_text = " ".join(s["text"] for s in segments)
    return {"segments": segments, "full_text": full_text}


def parse_txt(text: str) -> dict:
    """Parse plain text as a single segment (no timestamps).

    Returns {"segments": [...], "full_text": "..."} like the transcriber.
    """
    # Clean up excessive whitespace
    text = text.strip()
    # Try to detect if it's already line-by-line segments
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) > 1:
        # Treat each non-empty line as a segment with placeholder timestamps
        segments = [
            {"start": round(i * 5.0, 2), "end": round((i + 1) * 5.0, 2), "text": line}
            for i, line in enumerate(lines)
        ]
    else:
        segments = [
            {"start": 0.0, "end": 5.0, "text": text}
        ]
    full_text = " ".join(s["text"] for s in segments)
    return {"segments": segments, "full_text": full_text}


def detect_and_parse(content: str, filename: str = "") -> dict:
    """Auto-detect subtitle format and parse.

    Args:
        content: The raw text content of the subtitle file.
        filename: Optional filename to help detect format.

    Returns:
        {"segments": [...], "full_text": "..."}
    """
    lower = filename.lower()

    if lower.endswith(".vtt") or content.strip().startswith("WEBVTT"):
        logger.info("Detected VTT format for %s", filename)
        return parse_vtt(content)

    if lower.endswith(".srt") or _TIMESTAMP_RE.search(content):
        logger.info("Detected SRT format for %s", filename)
        return parse_srt(content)

    # Default: plain text
    logger.info("Treating %s as plain text", filename)
    return parse_txt(content)
