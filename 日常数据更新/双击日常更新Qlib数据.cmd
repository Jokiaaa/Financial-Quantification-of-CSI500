@echo off
chcp 65001 >nul
set "PYTHON=C:\Users\30855\Desktop\RSRS\.venv-qlib\Scripts\python.exe"
"%PYTHON%" "%~dp0daily_qlib_update.py" update
if errorlevel 1 goto failed
echo.
echo Qlib data update completed.
goto done
:failed
echo.
echo Qlib data update failed. Check daily_update_runs for details.
:done
pause
