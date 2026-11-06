@echo off
setlocal
cd /d "%~dp0"
py -3 -c "import sys; sys.exit(sys.version_info < (3,9))" >nul 2>&1
if not errorlevel 1 (
    py -3 -B launch.py %*
    goto :done
)
python -c "import sys; sys.exit(sys.version_info < (3,9))" >nul 2>&1
if not errorlevel 1 (
    python -B launch.py %*
    goto :done
)
echo Python 3.9+ is required: https://www.python.org/downloads/
echo During installation, select Add Python to PATH.
pause
exit /b 1
:done
if errorlevel 1 pause
