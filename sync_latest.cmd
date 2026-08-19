@echo off
setlocal

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync_latest_and_push.ps1"
set "SYNC_EXIT=%ERRORLEVEL%"

echo.
if not "%SYNC_EXIT%"=="0" (
    echo Sync failed. Review the error above.
) else (
    echo Done. You can close this window.
)

pause
exit /b %SYNC_EXIT%
