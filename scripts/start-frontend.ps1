<#
.SYNOPSIS
  Inicia la interfaz web en http://localhost:3000
.PARAMETER Prod
  Compila y ejecuta en modo producción (más rápido para presentar).
.PARAMETER Lan
  Escucha en todas las interfaces (para abrir desde un teléfono en la misma red).
#>
param([switch]$Prod, [switch]$Lan)
. "$PSScriptRoot\_common.ps1"
if (-not (Test-Path (Join-Path $Frontend "node_modules"))) { Fail "Faltan dependencias. Ejecute primero: scripts\setup.ps1" }
Push-Location $Frontend
try {
  $hostArgs = @()
  if ($Lan) { $hostArgs = @("-H", "0.0.0.0") }
  if ($Prod) {
    Write-Step "Compilando (modo producción)"
    npm run build
    if ($LASTEXITCODE -ne 0) { Fail "Falló la compilación." }
    Write-Step "Interfaz en http://localhost:3000"
    npx next start -p 3000 @hostArgs
  } else {
    Write-Step "Interfaz en http://localhost:3000 (modo desarrollo)"
    npx next dev -p 3000 @hostArgs
  }
} finally { Pop-Location }
