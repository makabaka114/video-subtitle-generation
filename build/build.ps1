$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
}

& .\.venv\Scripts\python -m pip install --upgrade pip
& .\.venv\Scripts\python -m pip install -e .
& .\.venv\Scripts\pyinstaller --noconfirm subtitle_tool.spec

$runtimeDlls = @(
    "msvcp140.dll",
    "MSVCP140_1.dll",
    "ucrtbase.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll"
)

$internalDir = Join-Path $root "dist\offline_subtitle_tool\_internal"
foreach ($dll in $runtimeDlls) {
    $target = Join-Path $internalDir $dll
    if (Test-Path $target) {
        Remove-Item -Force $target
    }
}
