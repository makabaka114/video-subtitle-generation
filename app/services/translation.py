from __future__ import annotations

import json
import os
import re
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.models import SubtitleSegment
from app.paths import (
    ARGOS_CACHE_DIR,
    ARGOS_CONFIG_DIR,
    ARGOS_DATA_DIR,
    ARGOS_PACKAGES_DIR,
    ensure_app_dirs,
)

ensure_app_dirs()
os.environ["XDG_DATA_HOME"] = str(ARGOS_DATA_DIR)
os.environ["XDG_CACHE_HOME"] = str(ARGOS_CACHE_DIR)
os.environ["XDG_CONFIG_HOME"] = str(ARGOS_CONFIG_DIR)
os.environ["ARGOS_PACKAGES_DIR"] = str(ARGOS_PACKAGES_DIR)

import ctranslate2
from argostranslate.package import Package, get_installed_packages
from argostranslate.tokenizer import BPETokenizer, SentencePieceTokenizer


SUPPORTED_BILINGUAL_LANGUAGES = {"zh", "en", "ja", "ko"}
PACKAGE_INDEX_URL = "https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json"
PACKAGE_INDEX_PATH = ARGOS_DATA_DIR / "argos-translate" / "index.json"
PACKAGE_DOWNLOADS_DIR = ARGOS_CACHE_DIR / "argos-translate" / "downloads"


@dataclass(slots=True)
class AvailablePackageRecord:
    from_code: str | None
    to_code: str | None
    links: list[str]
    type: str


class TranslationError(RuntimeError):
    """离线翻译失败。"""


class OfflineTranslator:
    def __init__(self) -> None:
        self._package_dir = ARGOS_PACKAGES_DIR
        self._package_dir.mkdir(parents=True, exist_ok=True)
        PACKAGE_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        PACKAGE_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    def build_bilingual_segments(
        self,
        detected_language: str | None,
        segments: list[SubtitleSegment],
    ) -> tuple[list[SubtitleSegment], list[str]]:
        language = (detected_language or "").lower()
        warnings: list[str] = []
        if language == "zh":
            return segments, warnings
        if language not in SUPPORTED_BILINGUAL_LANGUAGES:
            warnings.append(
                f"检测到语言 {language or 'unknown'} 暂未进入双语首版覆盖，已仅输出原文字幕。"
            )
            return segments, warnings

        if language == "en":
            return self._translate_segments("en", "zh", segments), warnings
        if language == "ja":
            interim = self._translate_segments("ja", "en", segments)
            return self._translate_segments("en", "zh", interim, source_attr="translated_text"), warnings
        if language == "ko":
            interim = self._translate_segments("ko", "en", segments)
            return self._translate_segments("en", "zh", interim, source_attr="translated_text"), warnings

        return segments, warnings

    def _translate_segments(
        self,
        from_code: str,
        to_code: str,
        segments: list[SubtitleSegment],
        source_attr: str = "original_text",
    ) -> list[SubtitleSegment]:
        package = self._ensure_package(from_code, to_code)
        translator = ctranslate2.Translator(
            str(package.package_path / "model"),
            device="cpu",
            compute_type="int8",
            inter_threads=1,
            intra_threads=0,
        )
        sentencizer = _SimpleSentencizer()

        translated_segments: list[SubtitleSegment] = []
        for segment in segments:
            source_text = getattr(segment, source_attr)
            if not source_text:
                translated_segments.append(segment)
                continue
            translated_text = self._translate_text(package, translator, sentencizer, source_text).strip()
            translated_segments.append(
                SubtitleSegment(
                    start=segment.start,
                    end=segment.end,
                    original_text=segment.original_text,
                    translated_text=translated_text,
                )
            )
        return translated_segments

    def _translate_text(
        self,
        package: Package,
        translator: ctranslate2.Translator,
        sentencizer: "_SimpleSentencizer",
        text: str,
    ) -> str:
        sentences = sentencizer.split_sentences(text)
        tokenized = [package.tokenizer.encode(sentence) for sentence in sentences if sentence.strip()]
        if not tokenized:
            return text

        target_prefix = None
        package_target_prefix = getattr(package, "target_prefix", "")
        if package_target_prefix:
            target_prefix = [[package_target_prefix]] * len(tokenized)

        translated_batches = translator.translate_batch(
            tokenized,
            target_prefix=target_prefix,
            replace_unknowns=True,
            max_batch_size=32,
            batch_type="tokens",
            beam_size=4,
            num_hypotheses=1,
            length_penalty=0.2,
            return_scores=False,
        )

        translated_tokens: list[str] = []
        for batch in translated_batches:
            translated_tokens.extend(batch.hypotheses[0])

        value = package.tokenizer.decode(translated_tokens)
        if package_target_prefix and value.startswith(package_target_prefix):
            value = value[len(package_target_prefix) :]
        if value.startswith(" "):
            value = value[1:]
        return value

    def _ensure_package(self, from_code: str, to_code: str) -> Package:
        package = self._get_installed_package(from_code, to_code)
        if package is not None:
            return package

        available = self._load_available_packages()
        record = next(
            (
                item
                for item in available
                if item.type == "translate" and item.from_code == from_code and item.to_code == to_code
            ),
            None,
        )
        if record is None:
            raise TranslationError(f"未找到 {from_code} -> {to_code} 的离线翻译包。")

        archive_path = self._download_package(record)
        self._install_package_archive(archive_path)
        package = self._get_installed_package(from_code, to_code)
        if package is None:
            raise TranslationError(f"翻译包已安装，但仍无法建立 {from_code} -> {to_code} 翻译器。")
        return package

    def _get_installed_package(self, from_code: str, to_code: str) -> Package | None:
        for package in get_installed_packages():
            if package.type == "translate" and package.from_code == from_code and package.to_code == to_code:
                if not hasattr(package, "tokenizer"):
                    package = self._reload_package(package.package_path)
                return package
        return None

    def _reload_package(self, package_path: Path) -> Package:
        package = Package(package_path)
        sp_model_path = package.package_path / "sentencepiece.model"
        bpe_model_path = package.package_path / "bpe.model"
        if sp_model_path.exists():
            package.tokenizer = SentencePieceTokenizer(sp_model_path)
        elif bpe_model_path.exists():
            package.tokenizer = BPETokenizer(bpe_model_path, package.from_code, package.to_code)
        else:
            raise TranslationError(f"翻译包 {package.package_path.name} 缺少分词模型。")
        return package

    def _load_available_packages(self) -> list[AvailablePackageRecord]:
        if not PACKAGE_INDEX_PATH.exists():
            self._update_package_index()
        try:
            raw = json.loads(PACKAGE_INDEX_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            self._update_package_index()
            try:
                raw = json.loads(PACKAGE_INDEX_PATH.read_text(encoding="utf-8"))
            except Exception as exc2:
                raise TranslationError(f"无法读取离线翻译包索引：{exc2}") from exc2

        return [
            AvailablePackageRecord(
                from_code=item.get("from_code"),
                to_code=item.get("to_code"),
                links=item.get("links", []),
                type=item.get("type", "translate"),
            )
            for item in raw
        ]

    def _update_package_index(self) -> None:
        try:
            with urllib.request.urlopen(PACKAGE_INDEX_URL) as response:
                PACKAGE_INDEX_PATH.write_bytes(response.read())
        except Exception as exc:
            raise TranslationError(f"无法更新离线翻译包索引：{exc}") from exc

    def _download_package(self, record: AvailablePackageRecord) -> Path:
        filename = f"translate-{record.from_code}_{record.to_code}.argosmodel"
        target = PACKAGE_DOWNLOADS_DIR / filename
        if target.exists():
            return target

        last_error: Exception | None = None
        for link in record.links:
            try:
                req = urllib.request.Request(link, headers={"User-Agent": "OfflineSubtitleTool"})
                with urllib.request.urlopen(req) as response:
                    target.write_bytes(response.read())
                return target
            except Exception as exc:
                last_error = exc

        raise TranslationError(f"下载翻译包失败：{last_error}")

    def _install_package_archive(self, archive_path: Path) -> None:
        if not zipfile.is_zipfile(archive_path):
            raise TranslationError("下载的翻译包不是有效的压缩包。")
        with zipfile.ZipFile(archive_path, "r") as archive:
            archive.extractall(path=ARGOS_PACKAGES_DIR)


class _SimpleSentencizer:
    _sentence_splitter = re.compile(r"(?<=[。！？!?\.])\s+|(?<=[。！？!?])")

    def split_sentences(self, text: str) -> list[str]:
        stripped = text.strip()
        if not stripped:
            return []
        parts = [part.strip() for part in self._sentence_splitter.split(stripped) if part.strip()]
        return parts or [stripped]
