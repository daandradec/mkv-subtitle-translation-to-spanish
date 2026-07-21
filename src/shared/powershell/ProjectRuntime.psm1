function Initialize-VideoToolProjectRuntime {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$SkillRoot
    )

    $resolvedSkillRoot = (Resolve-Path -LiteralPath $SkillRoot).Path
    $projectRoot = (Resolve-Path -LiteralPath (Join-Path $resolvedSkillRoot "..\..")).Path
    $sharedPowerShellDir = Join-Path $projectRoot "src\shared\powershell"
    $sharedPythonDir = Join-Path $projectRoot "src\shared\python"
    $skillPythonDir = Join-Path $resolvedSkillRoot "python"

    foreach ($requiredDirectory in @($sharedPowerShellDir, $sharedPythonDir, $skillPythonDir)) {
        if (!(Test-Path -LiteralPath $requiredDirectory -PathType Container)) {
            throw "Required project runtime directory not found: $requiredDirectory"
        }
    }

    $pythonPathParts = @($sharedPythonDir, $skillPythonDir)
    if ($env:PYTHONPATH) {
        $pythonPathParts += $env:PYTHONPATH
    }
    $env:PYTHONPATH = $pythonPathParts -join [System.IO.Path]::PathSeparator

    return [pscustomobject][ordered]@{
        ProjectRoot = $projectRoot
        SharedPowerShellDir = $sharedPowerShellDir
        SharedPythonDir = $sharedPythonDir
        SkillPythonDir = $skillPythonDir
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

    $outputRoot = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "output")).TrimEnd('\', '/')
    $target = [System.IO.Path]::GetFullPath($OutputDir).TrimEnd('\', '/')
    $debugTarget = [System.IO.Path]::GetFullPath($DebugDir).TrimEnd('\', '/')
    if (Test-Path -LiteralPath $outputRoot) {
        $outputRootItem = Get-Item -LiteralPath $outputRoot -Force
        if (!$outputRootItem.PSIsContainer) {
            throw "Output root is not a directory: '$outputRoot'."
        }
        if ($outputRootItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            throw "Refusing to use a reparse-point output root: '$outputRoot'."
        }
    }
    if ([string]::Equals([System.IO.Path]::GetFileName($target), "_legacy", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Reserved output workspace target: '$target'."
    }
    $targetParent = [System.IO.Path]::GetDirectoryName($target)
    if (![string]::Equals($targetParent, $outputRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe output workspace target: '$target'. It must be a direct child of '$outputRoot'."
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

Export-ModuleMember -Function Initialize-VideoToolProjectRuntime, Initialize-VideoOutputWorkspace
