@echo off
REM ============================================================
REM  Opportunity Scout - 24/7 always-on mode
REM  Scans on the SCAN_INTERVAL_HOURS schedule (.env, default 6h)
REM  Sends a Telegram alert ONLY when a new opportunity appears.
REM  Keep this window open. Press Ctrl+C to stop.
REM ============================================================
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
echo Starting Opportunity Scout in 24/7 mode...
python main.py --schedule
echo.
echo Scout stopped. Press any key to close.
pause >nul
