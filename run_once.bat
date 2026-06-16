@echo off
REM ============================================================
REM  Opportunity Scout - single scan (for Windows Task Scheduler)
REM  Runs one scan; alerts Telegram only on NEW opportunities.
REM ============================================================
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
"C:\Users\Ramya\AppData\Local\Programs\Python\Python314\python.exe" main.py >> scout.log 2>&1
