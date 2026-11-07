<#
.SYNOPSIS
  Borra la base de datos local y las fotos subidas. Al iniciar el backend se recargan los datos demostrativos.
  Detenga el backend antes de ejecutarlo.
#>
. "$PSScriptRoot\_common.ps1"
$db = Join-Path $Root "database"
Get-ChildItem $db -Filter "mercacircular.db*" -ErrorAction SilentlyContinue | Remove-Item -Force
$media = Join-Path $db "media"
if (Test-Path $media) { Remove-Item $media -Recurse -Force }
Write-Step "Base de datos y fotos eliminadas. Inicie el backend para recargar la demostración."
