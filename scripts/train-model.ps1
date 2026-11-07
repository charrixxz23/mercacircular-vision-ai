<#
.SYNOPSIS
  Descarga Fruits-360 (≈ 400 MB, solo las carpetas usadas), reentrena el clasificador
  y vuelve a validar el detector de manchas. No es necesario para ejecutar la demo:
  el modelo entrenado ya viene en backend\models.
.PARAMETER Images
  Regenera también las imágenes de ejemplo de demo-data\images.
#>
param([switch]$Images)
. "$PSScriptRoot\_common.ps1"
Require-Venv
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "Se necesita Git: https://git-scm.com/download/win" }
& $VenvPython -m pip install -r (Join-Path $Root "requirements-ml.txt")
Push-Location $Backend
try {
  Write-Step "Descargando el subconjunto de Fruits-360"
  & $VenvPython -m ml.download_dataset; if ($LASTEXITCODE -ne 0) { Fail "Falló la descarga." }
  Write-Step "Entrenando y evaluando el clasificador"
  & $VenvPython -m ml.train; if ($LASTEXITCODE -ne 0) { Fail "Falló el entrenamiento." }
  Write-Step "Validando el detector de manchas (sintético)"
  & $VenvPython -m ml.evaluate_anomalies
  if ($Images) { & $VenvPython -m ml.make_demo_images }
  Write-Step "Listo. Reinicie el backend para cargar el modelo nuevo."
} finally { Pop-Location }
