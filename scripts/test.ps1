<#
.SYNOPSIS
  Ejecuta todas las pruebas automatizadas: backend (pytest) y frontend (tipos + vitest).
#>
. "$PSScriptRoot\_common.ps1"
Require-Venv
$failed = $false

Write-Step "Backend: pytest"
Push-Location $Backend
try { & $VenvPython -m pytest; if ($LASTEXITCODE -ne 0) { $failed = $true } } finally { Pop-Location }

Write-Step "Frontend: verificación de tipos y pruebas unitarias"
Push-Location $Frontend
try {
  npm run typecheck; if ($LASTEXITCODE -ne 0) { $failed = $true }
  npm test; if ($LASTEXITCODE -ne 0) { $failed = $true }
} finally { Pop-Location }

if ($failed) { Fail "Alguna prueba falló (ver arriba)." }
Write-Step "Todas las pruebas pasaron"
