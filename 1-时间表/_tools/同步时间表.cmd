@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
where %PY% >nul 2>nul || ( echo [ERROR] Python not found. & pause & exit /b 1 )
%PY% timeline.py %*
set RC=%errorlevel%
echo.
if not "%RC%"=="0" echo [ERROR] exit code %RC%.
pause
exit /b %RC%
