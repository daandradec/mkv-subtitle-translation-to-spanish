Set-StrictMode -Version Latest
$script:VideoProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))

function Get-VideoProjectRoot {
    return $script:VideoProjectRoot
}

function Initialize-VideoGeneratedEnvironment {
    [CmdletBinding()]
    param(
        [string]$ProjectRoot = "",
        [ValidateSet("system", "tests", "runtime")]
        [string]$TemporaryArea = "system"
    )

    if (!$ProjectRoot) {
        $ProjectRoot = Get-VideoProjectRoot
    }
    $ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\', '/')
    $temporaryRoot = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot ".tmp")).TrimEnd('\', '/')
    $cacheRoot = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot ".cache")).TrimEnd('\', '/')
    foreach ($generatedRoot in @($temporaryRoot, $cacheRoot)) {
        $expectedParent = [System.IO.Path]::GetDirectoryName($generatedRoot)
        if (![string]::Equals($expectedParent, $ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Unsafe generated root: $generatedRoot"
        }

        if (Test-Path -LiteralPath $generatedRoot) {
            $generatedRootItem = Get-Item -LiteralPath $generatedRoot -Force
            if (!$generatedRootItem.PSIsContainer -or ($generatedRootItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
                throw "The repository generated root must be a regular directory: $generatedRoot"
            }
        }
        else {
            New-Item -ItemType Directory -Path $generatedRoot | Out-Null
        }
    }

    $paths = [ordered]@{
        Root = $temporaryRoot
        System = Join-Path $temporaryRoot "system"
        Tests = Join-Path $temporaryRoot "tests"
        Runtime = Join-Path $temporaryRoot "runtime"
        Build = Join-Path $temporaryRoot "build"
        Logs = Join-Path $temporaryRoot "logs"
        CacheRoot = $cacheRoot
        PipCache = Join-Path $cacheRoot "pip"
        PythonCache = Join-Path $cacheRoot "python"
        Models = Join-Path $cacheRoot "models"
        HuggingFace = Join-Path $cacheRoot "models\huggingface"
        Torch = Join-Path $cacheRoot "models\torch"
        Whisper = Join-Path $cacheRoot "models\whisper"
        Cache = Join-Path $cacheRoot "runtime"
        State = Join-Path $cacheRoot "install-state"
        Packages = Join-Path $cacheRoot "packages"
        PythonPackages = Join-Path $cacheRoot "packages\python"
    }
    $requiredPaths = @(
        $paths.Root,
        $paths.PipCache,
        $paths.PythonCache,
        $paths.Models,
        $paths.HuggingFace,
        $paths.Torch,
        $paths.Whisper,
        $paths.Cache,
        $paths.State,
        $paths.Packages,
        $paths.PythonPackages
    )
    $processTemporaryDirectory = switch ($TemporaryArea) {
        "tests" { $paths.Tests }
        "runtime" { $paths.Runtime }
        default { $paths.System }
    }
    $requiredPaths += $processTemporaryDirectory
    foreach ($path in $requiredPaths) {
        if (!(Test-Path -LiteralPath $path -PathType Container)) {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
        }
    }

    $env:VIDEO_TOOLKIT_TMP_ROOT = $paths.Root
    $env:VIDEO_TOOLKIT_CACHE_ROOT = $paths.CacheRoot
    $env:VIDEO_TOOLKIT_TEMP_CATEGORY = $TemporaryArea
    $env:TEMP = $processTemporaryDirectory
    $env:TMP = $processTemporaryDirectory
    $env:TMPDIR = $processTemporaryDirectory
    $env:PIP_CACHE_DIR = $paths.PipCache
    $env:PYTHONPYCACHEPREFIX = $paths.PythonCache
    $env:HF_HOME = $paths.HuggingFace
    $env:HUGGINGFACE_HUB_CACHE = Join-Path $paths.HuggingFace "hub"
    $env:TORCH_HOME = $paths.Torch
    $env:WHISPER_CACHE_DIR = $paths.Whisper
    $env:XDG_CACHE_HOME = $paths.Cache

    return [pscustomobject]$paths
}

function Assert-NoGeneratedArtifactsAtRepositoryRoot {
    [CmdletBinding()]
    param([string]$ProjectRoot = "")

    if (!$ProjectRoot) {
        $ProjectRoot = Get-VideoProjectRoot
    }
    $ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
    $forbidden = @(
        (Join-Path $ProjectRoot "build"),
        (Join-Path $ProjectRoot "video_toolkit_workflows.egg-info")
    )
    $found = @($forbidden | Where-Object { Test-Path -LiteralPath $_ })
    if ($found.Count -gt 0) {
        throw "Temporary packaging artifacts escaped .tmp: $($found -join ', ')"
    }
}

function Remove-VideoTemporaryChild {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$TemporaryRoot,
        [Parameter(Mandatory = $true)]
        [string]$ChildName
    )

    if ($ChildName -notmatch '^[A-Za-z0-9._-]+$') {
        throw "Unsafe temporary child name: $ChildName"
    }
    $resolvedTemporaryRoot = [System.IO.Path]::GetFullPath($TemporaryRoot).TrimEnd('\', '/')
    $target = [System.IO.Path]::GetFullPath((Join-Path $resolvedTemporaryRoot $ChildName)).TrimEnd('\', '/')
    $targetParent = [System.IO.Path]::GetDirectoryName($target)
    if (![string]::Equals($targetParent, $resolvedTemporaryRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean a path outside the temporary root: $target"
    }
    if (Test-Path -LiteralPath $target) {
        $targetItem = Get-Item -LiteralPath $target -Force
        if (!$targetItem.PSIsContainer -or ($targetItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw "Refusing to clean a non-directory or reparse point: $target"
        }
        Remove-Item -LiteralPath $target -Recurse -Force
    }
}

function Remove-VideoCacheChild {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$CacheRoot,
        [Parameter(Mandatory = $true)]
        [string]$ChildName
    )

    if ($ChildName -notmatch '^[A-Za-z0-9._-]+$') {
        throw "Unsafe cache child name: $ChildName"
    }
    $resolvedCacheRoot = [System.IO.Path]::GetFullPath($CacheRoot).TrimEnd('\', '/')
    $target = [System.IO.Path]::GetFullPath((Join-Path $resolvedCacheRoot $ChildName)).TrimEnd('\', '/')
    $targetParent = [System.IO.Path]::GetDirectoryName($target)
    if (![string]::Equals($targetParent, $resolvedCacheRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean a path outside the cache root: $target"
    }
    if (Test-Path -LiteralPath $target) {
        $targetItem = Get-Item -LiteralPath $target -Force
        if (!$targetItem.PSIsContainer -or ($targetItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw "Refusing to clean a non-directory or reparse point: $target"
        }
        Remove-Item -LiteralPath $target -Recurse -Force
    }
}

function Initialize-VideoToolProjectRuntime {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$SkillRoot
    )

    $resolvedSkillRoot = (Resolve-Path -LiteralPath $SkillRoot).Path
    $projectRoot = (Resolve-Path -LiteralPath (Join-Path $resolvedSkillRoot "..\..")).Path
    $scriptsDir = Join-Path $projectRoot "scripts"
    $sharedSourceDir = Join-Path $projectRoot "src\shared"
    $skillPythonDir = Join-Path $resolvedSkillRoot "python"

    foreach ($requiredDirectory in @($scriptsDir, $sharedSourceDir, $skillPythonDir)) {
        if (!(Test-Path -LiteralPath $requiredDirectory -PathType Container)) {
            throw "Required project runtime directory not found: $requiredDirectory"
        }
    }

    $temporaryPaths = Initialize-VideoGeneratedEnvironment -ProjectRoot $projectRoot -TemporaryArea runtime

    $pythonPathParts = @($sharedSourceDir, $skillPythonDir)
    if ($env:PYTHONPATH) {
        $pythonPathParts += $env:PYTHONPATH
    }
    $env:PYTHONPATH = $pythonPathParts -join [System.IO.Path]::PathSeparator

    return [pscustomobject][ordered]@{
        ProjectRoot = $projectRoot
        ScriptsDir = $scriptsDir
        SharedSourceDir = $sharedSourceDir
        SkillPythonDir = $skillPythonDir
        TemporaryRoot = $temporaryPaths.Root
    }
}

function Initialize-VideoOutputWorkspace {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot,
        [Parameter(Mandatory = $true)]
        [string]$OutputDir,
        [Parameter(Mandatory = $true)]
        [string]$DebugDir,
        [Parameter(Mandatory = $true)]
        [string]$InputPath,
        [Parameter(Mandatory = $true)]
        [string]$Workflow,
        [switch]$Resume
    )

    $outputsRoot = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "outputs")).TrimEnd('\', '/')
    $target = [System.IO.Path]::GetFullPath($OutputDir).TrimEnd('\', '/')
    $debugTarget = [System.IO.Path]::GetFullPath($DebugDir).TrimEnd('\', '/')
    if (Test-Path -LiteralPath $outputsRoot) {
        $outputsRootItem = Get-Item -LiteralPath $outputsRoot -Force
        if (!$outputsRootItem.PSIsContainer) {
            throw "Outputs root is not a directory: '$outputsRoot'."
        }
        if ($outputsRootItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            throw "Refusing to use a reparse-point outputs root: '$outputsRoot'."
        }
    }
    if ([string]::Equals([System.IO.Path]::GetFileName($target), "_legacy", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Reserved output workspace target: '$target'."
    }
    $targetParent = [System.IO.Path]::GetDirectoryName($target)
    if (![string]::Equals($targetParent, $outputsRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe output workspace target: '$target'. It must be a direct child of '$outputsRoot'."
    }
    $targetPrefix = $target + [System.IO.Path]::DirectorySeparatorChar
    if (!$debugTarget.StartsWith($targetPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe debug workspace target: '$debugTarget'. It must be inside '$target'."
    }

    if ($Resume) {
        if (!(Test-Path -LiteralPath $target -PathType Container)) {
            throw "Cannot resume because the deterministic output workspace does not exist: $target"
        }
    }
    elseif (Test-Path -LiteralPath $target) {
        $targetItem = Get-Item -LiteralPath $target -Force
        if (!$targetItem.PSIsContainer) {
            throw "Output workspace target is not a directory: $target"
        }
        if ($targetItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            throw "Refusing to clear a reparse-point output workspace: $target"
        }
        $reparsePoint = Get-ChildItem -LiteralPath $target -Force -Recurse -ErrorAction Stop |
            Where-Object { $_.Attributes -band [System.IO.FileAttributes]::ReparsePoint } |
            Select-Object -First 1
        if ($reparsePoint) {
            throw "Refusing to clear an output workspace containing a reparse point: $($reparsePoint.FullName)"
        }
        foreach ($child in (Get-ChildItem -LiteralPath $target -Force)) {
            Remove-Item -LiteralPath $child.FullName -Recurse -Force
        }
    }

    foreach ($directory in @($target, $debugTarget)) {
        if (!(Test-Path -LiteralPath $directory -PathType Container)) {
            New-Item -ItemType Directory -Path $directory -Force | Out-Null
        }
    }

    $manifestPath = Join-Path $debugTarget "run_manifest.json"
    [ordered]@{
        schema_version = 1
        workflow = $Workflow
        mode = if ($Resume) { "resume" } else { "fresh" }
        input_path = [System.IO.Path]::GetFullPath($InputPath)
        output_dir = $target
        debug_dir = $debugTarget
        initialized_at_utc = [DateTime]::UtcNow.ToString("o")
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    return [pscustomobject][ordered]@{
        OutputDir = $target
        DebugDir = $debugTarget
        Manifest = $manifestPath
        Mode = if ($Resume) { "resume" } else { "fresh" }
    }
}

Export-ModuleMember -Function `
    Get-VideoProjectRoot, `
    Initialize-VideoGeneratedEnvironment, `
    Assert-NoGeneratedArtifactsAtRepositoryRoot, `
    Remove-VideoTemporaryChild, `
    Remove-VideoCacheChild, `
    Initialize-VideoToolProjectRuntime, `
    Initialize-VideoOutputWorkspace
