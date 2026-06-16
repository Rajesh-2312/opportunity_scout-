@echo off
REM ============================================================
REM  Opportunity Scout - investment monitor (Windows Task)
REM  Checks recommended stocks' live prices; sends an INSTANT
REM  Telegram SELL alert on loss / book-profit alert on target.
REM ============================================================
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
"C:\Users\Ramya\AppData\Local\Programs\Python\Python314\python.exe" main.py --monitor >> monitor.log 2>&1
