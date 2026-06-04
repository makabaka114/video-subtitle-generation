@echo off
setlocal
set "APP_DIR=%~dp0dist\offline_subtitle_tool"
set "APP_EXE=%APP_DIR%\offline_subtitle_tool.exe"

if not exist "%APP_EXE%" (
    echo 未找到可执行文件：
    echo %APP_EXE%
    echo.
    echo 请先完成打包，或确认 dist 目录没有被移动。
    pause
    exit /b 1
)

start "" "%APP_EXE%"
