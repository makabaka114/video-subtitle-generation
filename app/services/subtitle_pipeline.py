from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from app.models import SubtitleJobConfig, SubtitleJobResult
from app.services.asr import RecognitionError, WhisperRecognizer
from app.services.events import ProgressEvent
from app.services.srt_writer import write_srt


ProgressCallback = Callable[[ProgressEvent], None]


class SubtitlePipeline:
    def __init__(self) -> None:
        self._recognizer = WhisperRecognizer()
        self._translator = None

    def run(
        self,
        config: SubtitleJobConfig,
        progress: ProgressCallback,
    ) -> SubtitleJobResult:
        start_time = time.perf_counter()
        warnings: list[str] = []
        try:
            self._emit(progress, "preparing", "正在准备任务...", 5)
            self._validate_input(config.input_path)

            self._emit(progress, "downloading_model", "正在检查本地识别模型...", 15)
            recognition_result = self._recognizer.recognize(
                config.input_path,
                language_override=config.language_override,
                status_callback=lambda message: self._emit(progress, "downloading_model", message, 20),
            )
            warnings.extend(recognition_result.warnings)

            self._emit(progress, "recognizing", "语音识别完成，正在整理字幕片段...", 55)
            segments = recognition_result.segments

            self._emit(progress, "translating", "正在生成中文字幕...", 75)
            translator = self._get_translator()
            bilingual_segments, translation_warnings = translator.build_bilingual_segments(
                recognition_result.detected_language,
                segments,
            )
            warnings.extend(translation_warnings)

            self._emit(progress, "writing", "正在写入字幕文件...", 90)
            config.output_path.parent.mkdir(parents=True, exist_ok=True)
            write_srt(config.output_path, bilingual_segments)

            elapsed = time.perf_counter() - start_time
            self._emit(progress, "completed", "字幕生成完成。", 100)
            return SubtitleJobResult(
                status="success",
                detected_language=recognition_result.detected_language,
                subtitle_path=config.output_path,
                elapsed_seconds=elapsed,
                warnings=warnings,
            )
        except (RecognitionError, ValueError, OSError, RuntimeError) as exc:
            elapsed = time.perf_counter() - start_time
            self._emit(progress, "failed", f"处理失败：{exc}", 100)
            return SubtitleJobResult(
                status="failed",
                detected_language=None,
                subtitle_path=None,
                elapsed_seconds=elapsed,
                warnings=warnings,
                error_message=str(exc),
            )

    @staticmethod
    def default_output_path(input_path: Path) -> Path:
        return input_path.with_name(f"{input_path.stem}.zh-bilingual.srt")

    @staticmethod
    def _validate_input(input_path: Path) -> None:
        if not input_path.exists():
            raise ValueError("选择的视频文件不存在。")
        if input_path.suffix.lower() not in {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".wmv", ".flv"}:
            raise ValueError("当前版本仅支持常见视频格式。")

    @staticmethod
    def _emit(
        callback: ProgressCallback,
        stage: str,
        message: str,
        progress: int,
    ) -> None:
        callback(ProgressEvent(stage=stage, message=message, progress=progress))

    def _get_translator(self):
        if self._translator is None:
            from app.services.translation import OfflineTranslator

            self._translator = OfflineTranslator()
        return self._translator
