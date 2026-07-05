@echo off
setlocal
set "DIR=%~dp0"
if exist "%DIR%.venv\Scripts\activate.bat" (
    call "%DIR%.venv\Scripts\activate.bat"
)
python "%DIR%main.py" %*
endlocal
