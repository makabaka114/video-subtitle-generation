from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


JobStatus = Literal["success", "failed"]
ComputePreference = Literal["auto"]
SubtitleMode = Literal["bilingual_zh"]


@dataclass(slots=True)
class SubtitleJobConfig:
    input_path: Path
    output_path: Path
    language_override: str | None = None
    compute_preference: ComputePreference = "auto"
    subtitle_mode: SubtitleMode = "bilingual_zh"


@dataclass(slots=True)
class SubtitleSegment:
    start: float
    end: float
    original_text: str
    translated_text: str | None = None


@dataclass(slots=True)
class SubtitleJobResult:
    status: JobStatus
    detected_language: str | None
    subtitle_path: Path | None
    elapsed_seconds: float
    warnings: list[str] = field(default_factory=list)
    error_message: str | None = None
