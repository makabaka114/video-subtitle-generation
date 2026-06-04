# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

datas = []
binaries = []
hiddenimports = []

EXCLUDED_RUNTIME_DLLS = {
    "MSVCP140.dll",
    "MSVCP140_1.dll",
    "MSVCP140_ATOMIC_WAIT.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "ucrtbase.dll",
}

for package_name in ("faster_whisper", "av", "sentencepiece", "sacremoses"):
    collected = collect_all(package_name)
    datas += collected[0]
    binaries += collected[1]
    hiddenimports += collected[2]

binaries += collect_dynamic_libs("ctranslate2")
hiddenimports += [
    "vendor.ctranslate2",
    "vendor.ctranslate2.models",
    "argostranslate.package",
    "argostranslate.tokenizer",
]

binaries = [
    entry
    for entry in binaries
    if entry[0].split("/")[-1].split("\\")[-1] not in EXCLUDED_RUNTIME_DLLS
]

block_cipher = None

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["pyi_rth_ct2shim.py"],
    excludes=["torch", "torchvision", "torchaudio", "stanza", "spacy", "stanza.tests", "spacy.tests"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="offline_subtitle_tool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="offline_subtitle_tool",
)
