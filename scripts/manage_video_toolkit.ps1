param(
    [Parameter(Position = 0)]
    [ValidateSet(
        "setup-python-environment",
        "build-python-package",
        "run-test-suite",
        "clean-temporary-files",
        "clean-cache-files",
        "verify-repository",
        "help"
    )]
    [string]$Command = "help",
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
    [switch]$SkipInstall,
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$InfrastructureModule = Join-Path $PSScriptRoot "lib\VideoToolkit.Infrastructure.psm1"
Import-Module $InfrastructureModule -Force

if (!$ProjectRoot) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
else {
    $ProjectRoot = (Resolve-Path $ProjectRoot).Path
}

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
    }
    catch {
        return $false
    }
    return ($LASTEXITCODE -eq 0 -and ($version | Select-Object -First 1) -eq $PythonVersion)
}

function Find-Python312 {
    $candidates = @(
        [pscustomobject]@{ Parts = [string[]]@("py", "-$PythonVersion") }
        [pscustomobject]@{ Parts = [string[]]@("python$PythonVersion") }
        [pscustomobject]@{ Parts = [string[]]@("python") }
    )
    foreach ($candidate in $candidates) {
        if (Test-PythonVersion -CommandParts $candidate.Parts) {
            return $candidate.Parts
        }
    }
    throw "Python $PythonVersion no esta instalado o no esta disponible en PATH/py launcher."
}

function Invoke-ManagedSetupCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable,
        [string[]]$Arguments = @(),
        [Parameter(Mandatory = $true)]
        [string]$SetupLog,
        [switch]$Quiet
    )

    if ($Quiet) {
        & $Executable @Arguments *>> $SetupLog
    }
    else {
        & $Executable @Arguments
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE`: $Executable $($Arguments -join ' ')"
    }
}

function Invoke-SetupPythonEnvironment {
    param(
        [bool]$InstallDependencies = $true,
        [bool]$InstallCuda = $false,
        [bool]$EmitJson = $false,
        [bool]$Quiet = $false
    )

    $temporaryPaths = Initialize-VideoGeneratedEnvironment -ProjectRoot $ProjectRoot
    foreach ($workingDirectoryName in @("inputs", "outputs")) {
        $workingDirectory = Join-Path $ProjectRoot $workingDirectoryName
        if (!(Test-Path -LiteralPath $workingDirectory -PathType Container)) {
            New-Item -ItemType Directory -Path $workingDirectory -Force | Out-Null
        }
    }
    $resolvedVenvDir = if ($VenvDir) { [System.IO.Path]::GetFullPath($VenvDir) } else { Join-Path $ProjectRoot ".venv" }
    $resolvedRequirementsPath = if ($RequirementsPath) { [System.IO.Path]::GetFullPath($RequirementsPath) } else { Join-Path $ProjectRoot "requirements.txt" }
    $resolvedWhisperXRequirementsPath = if ($WhisperXRequirementsPath) { [System.IO.Path]::GetFullPath($WhisperXRequirementsPath) } else { Join-Path $ProjectRoot "requirements-whisperx.txt" }
    $venvScriptsDir = Join-Path $resolvedVenvDir "Scripts"
    $venvPython = Join-Path $venvScriptsDir "python.exe"
    $requirementsMarker = Join-Path $temporaryPaths.State "requirements.sha256"
    $whisperXRequirementsMarker = Join-Path $temporaryPaths.State "requirements-whisperx.sha256"
    $setupLog = Join-Path $temporaryPaths.Logs "setup.log"
    if (!(Test-Path -LiteralPath $temporaryPaths.Logs -PathType Container)) {
        New-Item -ItemType Directory -Path $temporaryPaths.Logs -Force | Out-Null
    }
    if (Test-Path -LiteralPath $setupLog) {
        Remove-Item -LiteralPath $setupLog -Force
    }
    $createdVenv = $false
    $installedRequirements = $false
    $installedWhisperXRequirements = $false
    $installedCudaTorch = $false
    $whisperXWarning = ""

    if ((Test-Path -LiteralPath $resolvedVenvDir -PathType Container) -and !(Test-Path -LiteralPath $venvPython)) {
        $existingEntry = Get-ChildItem -LiteralPath $resolvedVenvDir -Force | Select-Object -First 1
        if ($existingEntry) {
            throw "El entorno virtual existente no tiene la estructura de Windows esperada: $resolvedVenvDir. No compartas la misma .venv entre Windows y Ubuntu."
        }
    }
    if (!(Test-Path -LiteralPath $venvPython)) {
        $pythonCommand = Find-Python312
        Invoke-CommandParts -CommandParts $pythonCommand -ExtraArgs @("-m", "venv", $resolvedVenvDir)
        if ($LASTEXITCODE -ne 0) {
            throw "No se pudo crear el entorno virtual en $resolvedVenvDir."
        }
        $createdVenv = $true
    }

    $venvVersion = & $venvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ($LASTEXITCODE -ne 0 -or ($venvVersion | Select-Object -First 1) -ne $PythonVersion) {
        throw "El entorno virtual existe pero no usa Python ${PythonVersion}: $resolvedVenvDir"
    }

    $quietCommands = $Quiet -or $EmitJson
    $requirementsHash = if (Test-Path -LiteralPath $resolvedRequirementsPath) {
        (Get-FileHash -LiteralPath $resolvedRequirementsPath -Algorithm SHA256).Hash
    }
    else { "" }
    $previousHash = if (Test-Path -LiteralPath $requirementsMarker) {
        (Get-Content -LiteralPath $requirementsMarker -Raw).Trim()
    }
    else { "" }

    if ($InstallDependencies -and $requirementsHash -and $requirementsHash -ne $previousHash) {
        Invoke-ManagedSetupCommand -Executable $venvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel") -SetupLog $setupLog -Quiet:$quietCommands
        Invoke-ManagedSetupCommand -Executable $venvPython -Arguments @("-m", "pip", "install", "-r", $resolvedRequirementsPath) -SetupLog $setupLog -Quiet:$quietCommands
        Set-Content -LiteralPath $requirementsMarker -Value $requirementsHash -Encoding ASCII
        $installedRequirements = $true
    }

    $whisperXRequirementsHash = if (Test-Path -LiteralPath $resolvedWhisperXRequirementsPath) {
        (Get-FileHash -LiteralPath $resolvedWhisperXRequirementsPath -Algorithm SHA256).Hash
    }
    else { "" }
    $previousWhisperXHash = if (Test-Path -LiteralPath $whisperXRequirementsMarker) {
        (Get-Content -LiteralPath $whisperXRequirementsMarker -Raw).Trim()
    }
    else { "" }

    if ($InstallDependencies -and $whisperXRequirementsHash -and $whisperXRequirementsHash -ne $previousWhisperXHash) {
        try {
            Invoke-ManagedSetupCommand -Executable $venvPython -Arguments @("-m", "pip", "install", "-r", $resolvedWhisperXRequirementsPath) -SetupLog $setupLog -Quiet:$quietCommands
            Set-Content -LiteralPath $whisperXRequirementsMarker -Value $whisperXRequirementsHash -Encoding ASCII
            $installedWhisperXRequirements = $true
        }
        catch {
            $whisperXWarning = "No se pudo instalar WhisperX. Revisa .tmp\logs\setup.log; openai-whisper permanece como fallback."
            if (!$quietCommands) {
                Write-Warning $whisperXWarning
            }
        }
    }

    if ($InstallDependencies -and $InstallCuda) {
        & $venvPython -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)" *> $null
        if ($LASTEXITCODE -ne 0) {
            Invoke-ManagedSetupCommand -Executable $venvPython -Arguments @(
                "-m", "pip", "install", "--upgrade", "--force-reinstall",
                "torch==$TorchCudaVersion", "torchvision==$TorchVisionCudaVersion", "torchaudio==$TorchAudioCudaVersion",
                "--index-url", $TorchCudaIndexUrl
            ) -SetupLog $setupLog -Quiet:$quietCommands
            $installedCudaTorch = $true
        }
        & $venvPython -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)" *> $null
        if ($LASTEXITCODE -ne 0) {
            throw "PyTorch no tiene CUDA disponible dentro de .venv. Revisa .tmp\logs\setup.log."
        }
    }

    $missingExternalTools = @("ffmpeg", "ffprobe", "mkvmerge") |
        Where-Object { !(Get-Command $_ -ErrorAction SilentlyContinue) }
    $payload = [ordered]@{
        python = $venvPython
        venv_dir = $resolvedVenvDir
        scripts_dir = $venvScriptsDir
        requirements = $resolvedRequirementsPath
        whisperx_requirements = $resolvedWhisperXRequirementsPath
        created_venv = $createdVenv
        installed_requirements = $installedRequirements
        installed_whisperx_requirements = $installedWhisperXRequirements
        installed_cuda_torch = $installedCudaTorch
        whisperx_warning = $whisperXWarning
        missing_external_tools = @($missingExternalTools)
    }

    Remove-VideoTemporaryChild -TemporaryRoot $temporaryPaths.Root -ChildName "system"
    if (!$whisperXWarning) {
        Remove-VideoTemporaryChild -TemporaryRoot $temporaryPaths.Root -ChildName "logs"
    }
    Assert-NoGeneratedArtifactsAtRepositoryRoot -ProjectRoot $ProjectRoot
    if ($EmitJson) {
        $payload | ConvertTo-Json -Depth 3
    }
    elseif (!$Quiet) {
        Write-Host "Python environment: $venvPython"
        foreach ($missingTool in $missingExternalTools) {
            Write-Warning "Required external tool is not on PATH: $missingTool"
        }
    }
}

function Invoke-BuildPythonPackage {
    $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (!(Test-Path -LiteralPath $venvPython)) {
        Invoke-SetupPythonEnvironment -InstallDependencies:$false -Quiet:$true
    }
    $temporaryPaths = Initialize-VideoGeneratedEnvironment -ProjectRoot $ProjectRoot
    if (!(Test-Path -LiteralPath $temporaryPaths.PythonPackages -PathType Container)) {
        New-Item -ItemType Directory -Path $temporaryPaths.PythonPackages -Force | Out-Null
    }

    $buildSucceeded = $false
    Push-Location $ProjectRoot
    try {
        & $venvPython -m pip install --upgrade "build>=1.2" "setuptools>=68" wheel
        if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las herramientas de build." }
        & $venvPython -m build --wheel --outdir $temporaryPaths.PythonPackages
        if ($LASTEXITCODE -ne 0) { throw "La construccion del paquete fallo." }
        $buildSucceeded = $true
        Assert-NoGeneratedArtifactsAtRepositoryRoot -ProjectRoot $ProjectRoot
    }
    finally {
        Pop-Location
        if ($buildSucceeded) {
            foreach ($child in @("build", "video_toolkit_workflows.egg-info", "system", "logs")) {
                Remove-VideoTemporaryChild -TemporaryRoot $temporaryPaths.Root -ChildName $child
            }
        }
    }
    Write-Host "Cached Python package: $($temporaryPaths.PythonPackages)"
}

function Invoke-TestSuite {
    $temporaryPaths = Initialize-VideoGeneratedEnvironment -ProjectRoot $ProjectRoot -TemporaryArea tests
    $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (!(Test-Path -LiteralPath $venvPython)) {
        throw "No se encontro .venv. Ejecuta setup-python-environment primero."
    }
    $env:PYTHONDONTWRITEBYTECODE = "1"
    $testsSucceeded = $false
    Push-Location $ProjectRoot
    try {
        & $venvPython (Join-Path $ProjectRoot "tests\run_all.py")
        if ($LASTEXITCODE -ne 0) { throw "La suite de pruebas fallo con codigo $LASTEXITCODE." }
        $testsSucceeded = $true
        Assert-NoGeneratedArtifactsAtRepositoryRoot -ProjectRoot $ProjectRoot
    }
    finally {
        Pop-Location
        if ($testsSucceeded) {
            Remove-VideoTemporaryChild -TemporaryRoot $temporaryPaths.Root -ChildName "tests"
        }
    }
}

function Invoke-CleanTemporaryFiles {
    $temporaryPaths = Initialize-VideoGeneratedEnvironment -ProjectRoot $ProjectRoot
    $children = @("build", "video_toolkit_workflows.egg-info", "runtime", "tests", "system", "logs")
    foreach ($child in $children) {
        Remove-VideoTemporaryChild -TemporaryRoot $temporaryPaths.Root -ChildName $child
    }

    Assert-NoGeneratedArtifactsAtRepositoryRoot -ProjectRoot $ProjectRoot
    Write-Host "Temporary cleanup completed under: $($temporaryPaths.Root)"
}

function Invoke-CleanCacheFiles {
    $temporaryPaths = Initialize-VideoGeneratedEnvironment -ProjectRoot $ProjectRoot
    foreach ($child in @("pip", "python", "models", "runtime", "install-state", "packages")) {
        Remove-VideoCacheChild -CacheRoot $temporaryPaths.CacheRoot -ChildName $child
    }

    $projectPrefix = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    $cacheSearchRoots = @(".agents", "scripts", "src", "tests") |
        ForEach-Object { Join-Path $ProjectRoot $_ } |
        Where-Object { Test-Path -LiteralPath $_ -PathType Container }
    $pythonCaches = @($cacheSearchRoots | ForEach-Object {
        Get-ChildItem -LiteralPath $_ -Directory -Filter "__pycache__" -Recurse -Force -ErrorAction SilentlyContinue
    })
    foreach ($cache in $pythonCaches) {
        $cachePath = [System.IO.Path]::GetFullPath($cache.FullName)
        if (!$cachePath.StartsWith($projectPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean Python cache outside the repository: $cachePath"
        }
        if ($cache.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            throw "Refusing to remove Python cache reparse point: $cachePath"
        }
        Remove-Item -LiteralPath $cachePath -Recurse -Force
    }
    Remove-VideoTemporaryChild -TemporaryRoot $temporaryPaths.Root -ChildName "system"
    Assert-NoGeneratedArtifactsAtRepositoryRoot -ProjectRoot $ProjectRoot
    Write-Host "Cache cleanup completed under: $($temporaryPaths.CacheRoot)"
}

function Invoke-VerifyRepository {
    $required = @(
        ".agents", ".cache", ".tmp", ".venv", "inputs", "outputs", "scripts", "src", "tests",
        "pyproject.toml", "setup.cfg", "requirements.txt", "requirements-whisperx.txt",
        "scripts\manage_video_toolkit.ps1", "scripts\manage_video_toolkit.sh",
        "scripts\lib\VideoToolkit.Infrastructure.psm1",
        "scripts\lib\VideoToolkit.Infrastructure.sh"
    )
    $missing = @($required | Where-Object { !(Test-Path -LiteralPath (Join-Path $ProjectRoot $_)) })
    if ($missing.Count -gt 0) {
        throw "Repository verification failed; missing: $($missing -join ', ')"
    }
    $legacyWorkingDirectories = @("input", "output") |
        Where-Object { Test-Path -LiteralPath (Join-Path $ProjectRoot $_) }
    if ($legacyWorkingDirectories) {
        throw "Repository verification failed; legacy working directories are not allowed: $($legacyWorkingDirectories -join ', ')"
    }
    Assert-NoGeneratedArtifactsAtRepositoryRoot -ProjectRoot $ProjectRoot
    Write-Host "Repository structure verified: $ProjectRoot"
}

function Show-VideoToolkitHelp {
    @"
Video toolkit repository manager

Commands:
  setup-python-environment  Create/validate .venv and install runtime dependencies.
  build-python-package      Build an optional wheel under .cache/packages/python/.
  run-test-suite            Run permanent tests using .tmp/tests/ for temporary data.
  clean-temporary-files     Remove only ephemeral data under .tmp/.
  clean-cache-files         Remove reusable caches, models, state, and wheels under .cache/.
  verify-repository         Validate canonical paths and root cleanliness.
  help                      Show this help.
"@ | Write-Host
}

switch ($Command) {
    "setup-python-environment" {
        Invoke-SetupPythonEnvironment -InstallDependencies:(!$SkipInstall) -InstallCuda:$EnsureCudaTorch -EmitJson:$Json
    }
    "build-python-package" { Invoke-BuildPythonPackage }
    "run-test-suite" { Invoke-TestSuite }
    "clean-temporary-files" { Invoke-CleanTemporaryFiles }
    "clean-cache-files" { Invoke-CleanCacheFiles }
    "verify-repository" { Invoke-VerifyRepository }
    default { Show-VideoToolkitHelp }
}
