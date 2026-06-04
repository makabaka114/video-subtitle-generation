from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ProgressStage = Literal[
    "preparing",
    "downloading_model",
    "recognizing",
    "translating",
    "writing",
    "completed",
    "failed",
]


@dataclass(slots=True)
class ProgressEvent:
    stage: ProgressStage
    message: str
    progress: int
