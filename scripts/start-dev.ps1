param(
    [int]$Port = 8000
)

# Activar virtualenv si existe
if (Test-Path -Path ".venv\Scripts\Activate.ps1") {
    Write-Output "Activating virtualenv .venv"
    . .\.venv\Scripts\Activate.ps1
}

Write-Output "Starting Uvicorn on http://127.0.0.1:$Port"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port $Port
