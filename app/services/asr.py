from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import ctranslate2
from faster_whisper import WhisperModel

from app.models import SubtitleSegment
from app.paths import WHISPER_DIR, ensure_app_dirs


GPU_MODEL_NAME = "turbo"
CPU_MODEL_NAME = "small"
StatusCallback = Callable[[str], None]


@dataclass(slots=True)
class RecognitionResult:
    detected_language: str | None
    segments: list[SubtitleSegment]
    warnings: list[str]


class RecognitionError(RuntimeError):
    """语音识别失败。"""


class WhisperRecognizer:
    def __init__(self) -> None:
        ensure_app_dirs()
        self._model_cache_dir = WHISPER_DIR

    def recognize(
        self,
        video_path: Path,
        language_override: str | None = None,
        status_callback: StatusCallback | None = None,
    ) -> RecognitionResult:
        use_cuda = self._can_use_cuda()
        attempts: list[dict[str, str | None]] = []

        if use_cuda:
            attempts.append(
                {
                    "model_name": GPU_MODEL_NAME,
                    "device": "cuda",
                    "compute_type": "float16",
                    "warning": None,
                    "prepare_message": "正在准备 GPU 识别模型...",
                }
            )

        attempts.append(
            {
                "model_name": CPU_MODEL_NAME,
                "device": "cpu",
                "compute_type": "int8",
                "warning": None if not use_cuda else "未能使用 GPU，已自动回退到 CPU 模式。",
                "prepare_message": "正在准备本地识别模型...",
            }
        )

        last_error: Exception | None = None
        for attempt in attempts:
            try:
                self._notify(status_callback, str(attempt["prepare_message"]))
                model = WhisperModel(
                    str(attempt["model_name"]),
                    device=str(attempt["device"]),
                    compute_type=str(attempt["compute_type"]),
                    download_root=str(self._model_cache_dir),
                )

                self._notify(status_callback, "模型已就绪，正在识别语音内容...")
                segments, info = model.transcribe(
                    str(video_path),
                    language=language_override,
                    task="transcribe",
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 500},
                    word_timestamps=False,
                )

                segment_list = [
                    SubtitleSegment(
                        start=segment.start,
                        end=segment.end,
                        original_text=segment.text.strip(),
                    )
                    for segment in segments
                    if segment.text and segment.text.strip()
                ]
                if not segment_list:
                    raise RecognitionError("未识别到可写入字幕的语音内容。")

                warnings: list[str] = []
                if attempt["warning"]:
                    warnings.append(str(attempt["warning"]))
                return RecognitionResult(
                    detected_language=info.language,
                    segments=segment_list,
                    warnings=warnings,
                )
            except Exception as exc:  # pragma: no cover - runtime fallback path
                last_error = exc

        raise RecognitionError(f"语音识别初始化失败：{last_error}") from last_error

    @staticmethod
    def _notify(callback: StatusCallback | None, message: str) -> None:
        if callback is not None:
            callback(message)

    @staticmethod
    def _can_use_cuda() -> bool:
        try:
            return ctranslate2.get_cuda_device_count() > 0
        except Exception:
            return False
