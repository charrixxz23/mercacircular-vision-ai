<#
.SYNOPSIS
  Abre dos ventanas: backend (puerto 8000) y frontend (puerto 3000), y luego el navegador.
.PARAMETER Prod
  Frontend en modo producción.
.PARAMETER Lan
  Permite abrir la app desde otros dispositivos de la red (por ejemplo, para escanear el QR).
#>
param([switch]$Prod, [switch]$Lan)
. "$PSScriptRoot\_common.ps1"
Require-Venv
$shell = if (Get-Command pwsh -ErrorAction SilentlyContinue) { "pwsh" } else { "powershell" }
$extra = @()
if ($Lan) { $extra += "-Lan" }
Start-Process $shell -ArgumentList (@("-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$PSScriptRoot\start-backend.ps1`"") + $extra)
Start-Sleep -Seconds 4
$fe = @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$PSScriptRoot\start-frontend.ps1`"") + $extra
if ($Prod) { $fe += "-Prod" }
Start-Process $shell -ArgumentList $fe
Write-Step "Esperando a que la interfaz responda en http://localhost:3000 ..."
for ($i = 0; $i -lt 90; $i++) {
  try { Invoke-WebRequest "http://localhost:3000" -UseBasicParsing -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep -Seconds 2 }
}
Start-Process "http://localhost:3000"
if ($Lan) {
  $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } | Select-Object -First 1).IPAddress
  Write-Host "Desde el teléfono (misma red Wi-Fi): http://$($ip):3000"
}
