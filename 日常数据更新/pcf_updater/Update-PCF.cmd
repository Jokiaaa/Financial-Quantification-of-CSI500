@echo off
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
set "PCF_PYTHON=C:\Users\30855\Desktop\DATA\.venv-qlib-run\Scripts\python.exe"
if not exist "%PCF_PYTHON%" (
  echo Python environment not found. See README.md.
  exit /b 1
)
"%PCF_PYTHON%" -u "%~dp0update_pcf.py" %*
set "PCF_EXIT=%ERRORLEVEL%"
echo.
echo Exit code: %PCF_EXIT%  [0=passed/plan, 2=held for review, 1=error]
exit /b %PCF_EXIT%
