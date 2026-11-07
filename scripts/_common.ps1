# Funciones compartidas por los scripts (compatibles con Windows PowerShell 5.1 y PowerShell 7).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
# $IsLinux / $IsMacOS no existen en Windows PowerShell 5.1: en ese caso se asume Windows.
$OnUnix = ($IsLinux -or $IsMacOS)
$VenvPython = if ($OnUnix) { Join-Path (Join-Path (Join-Path $Backend ".venv") "bin") "python" } else { Join-Path (Join-Path (Join-Path $Backend ".venv") "Scripts") "python.exe" }

function Write-Step($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Green }
function Fail($msg) { Write-Host ""; Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }

function Find-Python {
  # Prefiere el lanzador "py" de Windows; si no existe, usa "python".
  if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($v in @("3.13", "3.12", "3.11")) {
      & py "-$v" -c "import sys" 2>$null
      if ($LASTEXITCODE -eq 0) { return ,@("py", "-$v") }
    }
  }
  if (Get-Command python -ErrorAction SilentlyContinue) { return ,@("python") }
  if (Get-Command python3 -ErrorAction SilentlyContinue) { return ,@("python3") }
  Fail "No se encontró Python 3.11, 3.12 o 3.13. Instálelo desde https://www.python.org/downloads/ (marque 'Add python.exe to PATH')."
}

function Require-Venv {
  if (-not (Test-Path $VenvPython)) { Fail "Falta el entorno virtual. Ejecute primero: scripts\setup.ps1" }
}
