@echo off
cd /d "%~dp0"
set "PYW=pythonw"
where pyw >nul 2>nul && set "PYW=pyw -3"
for %%f in ("%~dp0*.pyw") do (
  start "" %PYW% "%%~ff"
  goto :done
)
echo [ERROR] no .pyw found.
pause
:done
