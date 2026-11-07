<#
.SYNOPSIS
  Inicia la API (FastAPI) en http://127.0.0.1:8000  ·  documentación: /docs
.PARAMETER Lan
  Escucha en todas las interfaces (para abrir la app desde un teléfono en la misma red).
#>
param([switch]$Lan)
. "$PSScriptRoot\_common.ps1"
Require-Venv
$hostAddr = if ($Lan) { "0.0.0.0" } else { "127.0.0.1" }
Push-Location $Backend
try {
  Write-Step "API en http://$($hostAddr):8000  (documentación: http://127.0.0.1:8000/docs)"
  & $VenvPython -m uvicorn app.main:app --host $hostAddr --port 8000 --reload
} finally { Pop-Location }
