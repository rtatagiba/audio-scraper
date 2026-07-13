@echo off
cd /d "%~dp0"
echo A iniciar o Audio Scraper... (a janela do browser abre sozinha)
".venv\Scripts\python.exe" app.py
pause
