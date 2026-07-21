param(
    [string]$ProjectRoot = "",
    [string]$PythonVersion = "3.12",
    [string]$VenvDir = "",
    [string]$RequirementsPath = "",
    [string]$WhisperXRequirementsPath = "",
    [string]$TorchCudaIndexUrl = "https://download.pytorch.org/whl/cu128",
    [string]$TorchCudaVersion = "2.8.0",
    [string]$TorchVisionCudaVersion = "0.23.0",
    [string]$TorchAudioCudaVersion = "2.8.0",
    [switch]$EnsureCudaTorch,
    [switch]$Json,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

if (!$ProjectRoot) {
    $ProjectRoot = Resolve-Path (Join-Path (Split-Path -Parent $PSCommandPath) "..\..\..")
}
$ProjectRoot = (Resolve-Path $ProjectRoot).Path

if (!$VenvDir) {
    $VenvDir = Join-Path $ProjectRoot ".venv"
}
if (!$RequirementsPath) {
    $RequirementsPath = Join-Path $ProjectRoot "requirements.txt"
}
if (!$WhisperXRequirementsPath) {
    $WhisperXRequirementsPath = Join-Path $ProjectRoot "requirements-whisperx.txt"
}

$ScriptsDir = Join-Path $VenvDir "Scripts"
$VenvPython = Join-Path $ScriptsDir "python.exe"
$RequirementsMarker = Join-Path $VenvDir ".requirements.sha256"
$WhisperXRequirementsMarker = Join-Path $VenvDir ".requirements-whisperx.sha256"

function Invoke-CommandParts {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$CommandParts,
        [string[]]$ExtraArgs = @()
    )

    $executable = $CommandParts[0]
    $baseArgs = @()
    if ($CommandParts.Count -gt 1) {
        $baseArgs = $CommandParts[1..($CommandParts.Count - 1)]
    }
    & $executable @baseArgs @ExtraArgs
}

function Test-PythonVersion {
    param([string[]]$CommandParts)

    $versionCode = "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    try {
        $version = Invoke-CommandParts -CommandParts $CommandParts -ExtraArgs @("-c", $versionCode) 2>$null
    } catch {
        return $false
    }
    if ($LASTEXITCODE -ne 0 -or !$version) {
        return $false
    }
    return (($version | Select-Object -First 1) -eq $PythonVersion)
}

function Find-Python312 {
    $candidates = @(
        @("py", "-$PythonVersion"),
        @("python$PythonVersion"),
        @("python")
    )

    foreach ($candidate in $candidates) {
        if (Test-PythonVersion -CommandParts $candidate) {
            return $candidate
        }
    }

    throw "Python $PythonVersion no esta instalado o no esta disponible en PATH/py launcher. Instala Python $PythonVersion y vuelve a ejecutar el flujo. En Windows puedes usar: choco install python312 -y, o winget install Python.Python.3.12."
}

function Invoke-SetupCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable,
        [string[]]$Arguments = @()
    )

    if ($Json) {
        $setupLog = Join-Path $VenvDir "setup.log"
        & $Executable @Arguments *>> $setupLog
    } else {
        & $Executable @Arguments
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE`: $Executable $($Arguments -join ' ')"
    }
}

$createdVenv = $false
$installedRequirements = $false
$installedWhisperXRequirements = $false
$installedCudaTorch = $false
$whisperXWarning = ""

if (!(Test-Path -LiteralPath $VenvPython)) {
    $pythonCommand = Find-Python312
    Invoke-CommandParts -CommandParts $pythonCommand -ExtraArgs @("-m", "venv", $VenvDir)
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo crear el entorno virtual en $VenvDir."
    }
    $createdVenv = $true
}

if (!(Test-Path -LiteralPath $VenvPython)) {
    throw "No se encontro el Python del entorno virtual esperado: $VenvPython"
}

$venvVersion = & $VenvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0 -or ($venvVersion | Select-Object -First 1) -ne $PythonVersion) {
    throw "El entorno virtual existe pero no usa Python $PythonVersion. Elimina o recrea '$VenvDir' con Python $PythonVersion."
}

$requirementsHash = ""
if (Test-Path -LiteralPath $RequirementsPath) {
    $requirementsHash = (Get-FileHash -LiteralPath $RequirementsPath -Algorithm SHA256).Hash
}
$previousHash = ""
if (Test-Path -LiteralPath $RequirementsMarker) {
    $previousHash = (Get-Content -LiteralPath $RequirementsMarker -Raw).Trim()
}

if (!$SkipInstall -and $requirementsHash -and $requirementsHash -ne $previousHash) {
    Invoke-SetupCommand -Executable $VenvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")
    Invoke-SetupCommand -Executable $VenvPython -Arguments @("-m", "pip", "install", "-r", $RequirementsPath)
    Set-Content -LiteralPath $RequirementsMarker -Value $requirementsHash -Encoding ASCII
    $installedRequirements = $true
}

$whisperXRequirementsHash = ""
if (Test-Path -LiteralPath $WhisperXRequirementsPath) {
    $whisperXRequirementsHash = (Get-FileHash -LiteralPath $WhisperXRequirementsPath -Algorithm SHA256).Hash
}
$previousWhisperXHash = ""
if (Test-Path -LiteralPath $WhisperXRequirementsMarker) {
    $previousWhisperXHash = (Get-Content -LiteralPath $WhisperXRequirementsMarker -Raw).Trim()
}

if (!$SkipInstall -and $whisperXRequirementsHash -and $whisperXRequirementsHash -ne $previousWhisperXHash) {
    try {
        Invoke-SetupCommand -Executable $VenvPython -Arguments @("-m", "pip", "install", "-r", $WhisperXRequirementsPath)
        Set-Content -LiteralPath $WhisperXRequirementsMarker -Value $whisperXRequirementsHash -Encoding ASCII
        $installedWhisperXRequirements = $true
    } catch {
        $whisperXWarning = "No se pudo instalar WhisperX en .venv. El flujo continuara con openai-whisper si esta disponible. Revisa .venv\setup.log para el detalle."
        if (!$Json) {
            Write-Warning $whisperXWarning
        }
    }
}

function Test-TorchCudaAvailable {
    $cudaCheck = @"
import sys
try:
    import torch
except Exception:
    sys.exit(2)
sys.exit(0 if torch.cuda.is_available() else 1)
"@
    & $VenvPython -c $cudaCheck *> $null
    return ($LASTEXITCODE -eq 0)
}

if (!$SkipInstall -and $EnsureCudaTorch) {
    if (!(Test-TorchCudaAvailable)) {
        Invoke-SetupCommand -Executable $VenvPython -Arguments @(
            "-m", "pip", "install",
            "--upgrade",
            "--force-reinstall",
            "torch==$TorchCudaVersion",
            "torchvision==$TorchVisionCudaVersion",
            "torchaudio==$TorchAudioCudaVersion",
            "--index-url",
            $TorchCudaIndexUrl
        )
        $installedCudaTorch = $true
    }
    if (!(Test-TorchCudaAvailable)) {
        throw "PyTorch no tiene CUDA disponible dentro de .venv despues de instalar desde $TorchCudaIndexUrl. Revisa driver NVIDIA, compatibilidad de GPU y el log .venv\setup.log."
    }
}

$payload = [ordered]@{
    python = $VenvPython
    venv_dir = $VenvDir
    scripts_dir = $ScriptsDir
    requirements = $RequirementsPath
    whisperx_requirements = $WhisperXRequirementsPath
    created_venv = $createdVenv
    installed_requirements = $installedRequirements
    installed_whisperx_requirements = $installedWhisperXRequirements
    installed_cuda_torch = $installedCudaTorch
    whisperx_warning = $whisperXWarning
}

if ($Json) {
    $payload | ConvertTo-Json -Depth 3
} else {
    Write-Host "Python environment: $VenvPython"
    if ($createdVenv) {
        Write-Host "Created virtual environment: $VenvDir"
    }
    if ($installedRequirements) {
        Write-Host "Installed requirements: $RequirementsPath"
    }
    if ($installedWhisperXRequirements) {
        Write-Host "Installed WhisperX requirements: $WhisperXRequirementsPath"
    }
    if ($installedCudaTorch) {
        Write-Host "Installed CUDA PyTorch from: $TorchCudaIndexUrl"
    }
}
