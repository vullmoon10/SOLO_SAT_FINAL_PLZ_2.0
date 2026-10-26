@echo off
cd /d "%~dp0"
set MINICONDA_PATH=C:\ProgramData\miniconda3

call "%MINICONDA_PATH%\Scripts\activate.bat" %MINICONDA_PATH%

python -m pip install -r requirements.txt
if errorlevel 1 (
    pause
    exit /b 1
)

python main.py
pause
