<#
.SYNOPSIS
  Instala todo lo necesario para ejecutar MercaCircular Vision AI en Windows.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
#>
. "$PSScriptRoot\_common.ps1"

Write-Step "Verificando Python"
$py = Find-Python
$ver = & $py[0] $py[1..9] -c "import sys; print('%d.%d' % sys.version_info[:2])"
Write-Host "Python $ver"
if ([version]$ver -lt [version]"3.11") { Fail "Se necesita Python 3.11 o superior (encontrado $ver)." }

Write-Step "Verificando Node.js"
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Fail "No se encontró Node.js. Instale la versión LTS (20 o 22) desde https://nodejs.org/" }
$node = (node -v).TrimStart("v")
Write-Host "Node $node"
if ([int]($node.Split(".")[0]) -lt 20) { Fail "Se necesita Node.js 20 o superior (encontrado $node)." }

Write-Step "Creando el entorno virtual de Python (backend\.venv)"
if (-not (Test-Path $VenvPython)) { & $py[0] $py[1..9] -m venv (Join-Path $Backend ".venv") }
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -r (Join-Path $Root "requirements-dev.txt")
if ($LASTEXITCODE -ne 0) { Fail "Falló la instalación de dependencias de Python." }

Write-Step "Instalando dependencias del frontend (npm)"
Push-Location $Frontend
try {
  if (Test-Path "package-lock.json") { npm ci --no-audit --no-fund } else { npm install --no-audit --no-fund }
  if ($LASTEXITCODE -ne 0) { Fail "Falló npm install." }
} finally { Pop-Location }

$envFile = Join-Path $Root ".env"
if (-not (Test-Path $envFile)) {
  Copy-Item (Join-Path $Root ".env.example") $envFile
  Write-Host "Se creó .env a partir de .env.example (valores por defecto)."
}

Write-Step "Listo"
Write-Host "Inicie la demo con:  powershell -ExecutionPolicy Bypass -File scripts\start.ps1"
