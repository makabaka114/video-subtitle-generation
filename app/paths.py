from __future__ import annotations

import sys
from pathlib import Path


def get_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


APP_DATA_DIR = get_app_root() / "app_data"
WHISPER_DIR = APP_DATA_DIR / "models" / "whisper"
ARGOS_ROOT_DIR = APP_DATA_DIR / "argos"
ARGOS_DATA_DIR = ARGOS_ROOT_DIR / "data"
ARGOS_CACHE_DIR = ARGOS_ROOT_DIR / "cache"
ARGOS_CONFIG_DIR = ARGOS_ROOT_DIR / "config"
ARGOS_PACKAGES_DIR = ARGOS_ROOT_DIR / "packages"


def ensure_app_dirs() -> None:
    for path in (
        APP_DATA_DIR,
        WHISPER_DIR,
        ARGOS_ROOT_DIR,
        ARGOS_DATA_DIR,
        ARGOS_CACHE_DIR,
        ARGOS_CONFIG_DIR,
        ARGOS_PACKAGES_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
