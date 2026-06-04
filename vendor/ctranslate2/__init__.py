import sys

if sys.platform == "win32":
    import ctypes
    import glob
    import os
    from importlib.resources import files

    package_dir = str(files(__name__))

    try:
        os.add_dll_directory(package_dir)
        os.add_dll_directory(f"{package_dir}/../_rocm_sdk_core/bin")
        os.add_dll_directory(f"{package_dir}/../_rocm_sdk_libraries_custom/bin")
    except (FileNotFoundError, OSError):
        pass

    for library in glob.glob(os.path.join(package_dir, "*.dll")):
        ctypes.CDLL(library)

from ctranslate2._ext import (
    AsyncGenerationResult,
    AsyncScoringResult,
    AsyncTranslationResult,
    DataType,
    Device,
    Encoder,
    EncoderForwardOutput,
    ExecutionStats,
    GenerationResult,
    GenerationStepResult,
    Generator,
    MpiInfo,
    ScoringResult,
    StorageView,
    TranslationResult,
    Translator,
    contains_model,
    get_cuda_device_count,
    get_supported_compute_types,
    set_random_seed,
)
from ctranslate2.extensions import register_extensions
from ctranslate2.logging import get_log_level, set_log_level
from ctranslate2.version import __version__

register_extensions()

from . import models  # noqa: E402,F401
