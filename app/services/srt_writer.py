from __future__ import annotations

from pathlib import Path

from app.models import SubtitleSegment


def _format_timestamp(seconds: float) -> str:
    total_milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(total_milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def write_srt(output_path: Path, segments: list[SubtitleSegment]) -> None:
    lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        lines.append(str(index))
        lines.append(
            f"{_format_timestamp(segment.start)} --> {_format_timestamp(segment.end)}"
        )
        lines.append(segment.original_text.strip())
        if segment.translated_text:
            lines.append(segment.translated_text.strip())
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
