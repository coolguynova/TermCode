$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path "$scriptDir\.venv\Scripts\Activate.ps1") {
    & "$scriptDir\.venv\Scripts\Activate.ps1"
}
python "$scriptDir\main.py" $args
