import importlib
import sys


if "ctranslate2" not in sys.modules:
    sys.modules["ctranslate2"] = importlib.import_module("vendor.ctranslate2")
