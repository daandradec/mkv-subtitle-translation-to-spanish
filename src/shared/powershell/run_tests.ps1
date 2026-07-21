param(
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

if (!$ProjectRoot) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
}
else {
    $ProjectRoot = (Resolve-Path $ProjectRoot).Path
}

$pythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (!(Test-Path -LiteralPath $pythonExe)) {
    throw "No se encontro el Python del entorno virtual: $pythonExe"
}

$env:PYTHONDONTWRITEBYTECODE = "1"
Push-Location $ProjectRoot
try {
    & $pythonExe (Join-Path $ProjectRoot "src\shared\tests\run_all.py")
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
