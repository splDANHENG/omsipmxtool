@echo off
cd /d "%~dp0"
if exist ".venv-gui\Scripts\python.exe" (
  ".venv-gui\Scripts\python.exe" -m omsimod.gui
) else if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m omsimod.gui
) else (
  echo Install Python 3.10+ and GUI dependencies as described in README.md first.
)
if errorlevel 1 pause
