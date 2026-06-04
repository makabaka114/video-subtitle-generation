@echo off
setlocal

set "ROOT=%~dp0"
set "APP_EXE=%ROOT%dist\offline_subtitle_tool\offline_subtitle_tool.exe"

if not exist "%APP_EXE%" (
    echo Could not find:
    echo %APP_EXE%
    echo.
    echo Please make sure the packaged app exists under dist\offline_subtitle_tool.
    pause
    exit /b 1
)

start "" "%APP_EXE%"
exit /b 0
