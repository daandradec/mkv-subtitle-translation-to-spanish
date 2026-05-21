param(
    [string]$InputVideo = "",
    [string]$WorkspaceId = "",
    [int]$AudioStreamIndex = -1,
    [ValidateSet("conservative", "balanced", "asr")]
    [string]$Profile = "conservative",
    [ValidateSet("mkv")]
    [string]$OutputFormat = "mkv",
    [switch]$KeepTemp,
    [switch]$GenerateSamples,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $PSCommandPath
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$InputDir = Join-Path $ProjectRoot "input"
$ModelPath = Join-Path $ProjectRoot "models\voice-cleaner\std.rnnn"
$CleanTitle = "Voz limpia FLAC"
$OriginalTitle = "Audio original"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Command,
        [string]$LogPath = ""
    )
    $executable = $Command[0]
    $arguments = @()
    if ($Command.Count -gt 1) {
        $arguments = $Command[1..($Command.Count - 1)]
    }
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $executable @arguments 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($LogPath) {
        $parent = Split-Path -Parent $LogPath
        if ($parent -and !(Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent | Out-Null
        }
        ($output | Out-String) | Set-Content -LiteralPath $LogPath -Encoding UTF8
    }
    if ($exitCode -ne 0) {
        throw "Command failed with exit code $exitCode`: $($Command -join ' ')`n$(($output | Out-String))"
    }
    return ($output | Out-String)
}

function Initialize-PythonEnvironment {
    $envJson = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ScriptDir "init_python_env.ps1") `
        -ProjectRoot $ProjectRoot `
        -Json
    if ($LASTEXITCODE -ne 0) {
        throw "Python environment initialization failed."
    }
    $envInfo = ($envJson | Out-String) | ConvertFrom-Json
    $env:VIRTUAL_ENV = [string]$envInfo.venv_dir
    $env:PATH = "$($envInfo.scripts_dir);$env:PATH"
    if ($envInfo.whisperx_warning) {
        Write-Warning ([string]$envInfo.whisperx_warning)
    }
    return [string]$envInfo.python
}

function Resolve-ProjectPath {
    param([string]$PathValue)
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return $PathValue
    }
    return (Join-Path $ProjectRoot $PathValue)
}

function Get-InputVideoCandidates {
    if (!(Test-Path -LiteralPath $InputDir)) {
        return @()
    }
    $candidates = @()
    foreach ($file in (Get-ChildItem -LiteralPath $InputDir -File)) {
        $probeJson = & ffprobe -v error `
            -show_entries stream=index,codec_type `
            -of json `
            $file.FullName
        if ($LASTEXITCODE -ne 0) {
            continue
        }
        $probe = ($probeJson | Out-String) | ConvertFrom-Json
        $streams = @($probe.streams)
        $hasVideo = @($streams | Where-Object { $_.codec_type -eq "video" }).Count -gt 0
        $hasAudio = @($streams | Where-Object { $_.codec_type -eq "audio" }).Count -gt 0
        if ($hasVideo -and $hasAudio) {
            $candidates += $file
        }
    }
    return @($candidates)
}

function Resolve-InputVideoPath {
    param(
        [string]$InputPath,
        [bool]$WasProvided
    )

    if (!$WasProvided -or [string]::IsNullOrWhiteSpace($InputPath)) {
        $candidates = Get-InputVideoCandidates
        if ($candidates.Count -eq 0) {
            throw "No se encontro ningun archivo de video con audio en 'input/'. Ubica un video o indica -InputVideo."
        }
        if ($candidates.Count -gt 1) {
            $names = ($candidates | ForEach-Object { $_.Name }) -join "', '"
            throw "Se encontraron multiples videos en 'input': '$names'. Indica exactamente uno con -InputVideo."
        }
        return $candidates[0].FullName
    }

    $candidatePaths = @()
    if ([System.IO.Path]::IsPathRooted($InputPath)) {
        $candidatePaths += $InputPath
    } else {
        $candidatePaths += (Join-Path $InputDir $InputPath)
        $candidatePaths += (Join-Path $ProjectRoot $InputPath)
    }
    foreach ($candidatePath in ($candidatePaths | Select-Object -Unique)) {
        if (Test-Path -LiteralPath $candidatePath) {
            return (Resolve-Path -LiteralPath $candidatePath).Path
        }
    }
    throw "No se encontro el archivo de video indicado: $InputPath."
}

function Select-AudioStream {
    param(
        [string]$InputPath,
        [int]$RequestedIndex
    )

    $probeJson = & ffprobe -v error `
        -select_streams a `
        -show_entries stream=index:stream_disposition=default:stream_tags=language,title `
        -of json `
        $InputPath
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudieron inspeccionar pistas de audio con ffprobe."
    }
    $probe = ($probeJson | Out-String) | ConvertFrom-Json
    $streams = @($probe.streams)
    if ($streams.Count -eq 0) {
        throw "No se encontraron pistas de audio para limpiar."
    }
    if ($RequestedIndex -ge 0) {
        foreach ($stream in $streams) {
            if ([int]$stream.index -eq $RequestedIndex) {
                return $stream
            }
        }
        throw "No se encontro la pista de audio con indice $RequestedIndex."
    }
    $defaultStreams = @($streams | Where-Object { $_.disposition -and [int]$_.disposition.default -eq 1 })
    if ($defaultStreams.Count -gt 0) {
        if ($defaultStreams.Count -gt 1) {
            $defaultIndexes = ($defaultStreams | ForEach-Object { "0:$([int]$_.index)" }) -join ", "
            Write-Warning "Se encontraron multiples pistas de audio default ($defaultIndexes). Se usara la primera; usa -AudioStreamIndex para elegir otra."
        }
        return $defaultStreams[0]
    }
    return $streams[0]
}

function Write-Report {
    param(
        [string]$Path,
        [hashtable]$Payload
    )
    $parent = Split-Path -Parent $Path
    if ($parent -and !(Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }
    $Payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Path -Encoding UTF8
}

$inputVideoWasProvided = $PSBoundParameters.ContainsKey("InputVideo")
foreach ($commandName in @("ffmpeg", "ffprobe", "mkvmerge")) {
    if ($null -eq (Get-Command $commandName -ErrorAction SilentlyContinue)) {
        throw "$commandName not found in PATH."
    }
}
if (!(Test-Path -LiteralPath $ModelPath)) {
    throw "No se encontro el modelo RNNoise requerido: $ModelPath"
}

$InputVideo = Resolve-InputVideoPath -InputPath $InputVideo -WasProvided $inputVideoWasProvided
$PythonExe = Initialize-PythonEnvironment

$workspaceArgs = @(
    (Join-Path $ScriptDir "voice_cleaner.py"),
    "workspace",
    "--input-video", $InputVideo,
    "--json"
)
if ($WorkspaceId) {
    $workspaceArgs += @("--workspace-id", $WorkspaceId)
}
$workspaceJson = & $PythonExe @workspaceArgs
if ($LASTEXITCODE -ne 0) {
    throw "Voice cleaner workspace path generation failed."
}
$workspaceInfo = ($workspaceJson | Out-String) | ConvertFrom-Json
$WorkspaceId = [string]$workspaceInfo.workspace_id
$WorkDir = Resolve-ProjectPath ([string]$workspaceInfo.work_dir)
$OutputDir = Resolve-ProjectPath ([string]$workspaceInfo.output_dir)
$PremasterFlac = Resolve-ProjectPath ([string]$workspaceInfo.premaster_flac)
$CleanFlac = Resolve-ProjectPath ([string]$workspaceInfo.clean_flac)
$OutputMkv = Resolve-ProjectPath ([string]$workspaceInfo.output_mkv)
$ReportPath = Resolve-ProjectPath ([string]$workspaceInfo.report)
$SamplesDir = Resolve-ProjectPath ([string]$workspaceInfo.samples_dir)

$selectedAudio = Select-AudioStream -InputPath $InputVideo -RequestedIndex $AudioStreamIndex
$selectedAudioIndex = [int]$selectedAudio.index
$selectedAudioLanguage = ""
if ($selectedAudio.tags -and $selectedAudio.tags.language) {
    $selectedAudioLanguage = [string]$selectedAudio.tags.language
}
$cleanAudioLanguage = $selectedAudioLanguage
if ([string]::IsNullOrWhiteSpace($cleanAudioLanguage)) {
    $cleanAudioLanguage = "und"
}

$chainJson = & $PythonExe (Join-Path $ScriptDir "voice_cleaner.py") `
    "chain" `
    "--profile" $Profile `
    "--model-path" "models/voice-cleaner/std.rnnn" `
    "--json"
if ($LASTEXITCODE -ne 0) {
    throw "Voice cleaner filter chain generation failed."
}
$chainInfo = ($chainJson | Out-String) | ConvertFrom-Json
$VoiceFilter = [string]$chainInfo.filter

Write-Host "Workspace: $WorkspaceId"
Write-Host "Selected audio stream: 0:$selectedAudioIndex"
if ($selectedAudioLanguage) {
    Write-Host "Selected audio language: $selectedAudioLanguage"
}
Write-Host "Profile: $Profile"

if ($DryRun) {
    Write-Host "Dry run; no audio cleaning or remux will be executed."
    Write-Host "Output MKV: $OutputMkv"
    Write-Host "Clean FLAC: $CleanFlac"
    Write-Host "Filter: $VoiceFilter"
    exit 0
}

foreach ($directory in @($WorkDir, $OutputDir)) {
    if (!(Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory | Out-Null
    }
}

Push-Location $ProjectRoot
try {
    $validateLog = Join-Path $WorkDir "validate_arnndn_model.txt"
    Invoke-Checked -Command @(
        "ffmpeg", "-hide_banner", "-y", "-v", "error",
        "-f", "lavfi", "-i", "anoisesrc=d=0.25:r=48000",
        "-af", "arnndn=m=models/voice-cleaner/std.rnnn:mix=0.25",
        "-f", "null", "NUL"
    ) -LogPath $validateLog | Out-Null

    $originalProbeJson = Join-Path $WorkDir "ffprobe_original.json"
    $originalProbe = Invoke-Checked -Command @(
        "ffprobe", "-hide_banner", "-show_format", "-show_streams", "-print_format", "json", $InputVideo
    ) -LogPath (Join-Path $WorkDir "ffprobe_original.log")
    $originalProbe | Set-Content -LiteralPath $originalProbeJson -Encoding UTF8

    Invoke-Checked -Command @(
        "ffmpeg", "-hide_banner", "-y", "-nostats",
        "-i", $InputVideo,
        "-map", "0:$selectedAudioIndex",
        "-vn",
        "-af", $VoiceFilter,
        "-c:a", "flac",
        "-sample_fmt", "s32",
        "-compression_level", "8",
        $PremasterFlac
    ) -LogPath (Join-Path $WorkDir "voice_cleaner_premaster.txt") | Out-Null

    $loudnormPass1Log = Join-Path $WorkDir "loudnorm_premaster_pass1.txt"
    $loudnormPass1Output = Invoke-Checked -Command @(
        "ffmpeg", "-hide_banner", "-y", "-nostats",
        "-i", $PremasterFlac,
        "-vn",
        "-af", "loudnorm=I=-16.0:LRA=9:TP=-2.0:print_format=json",
        "-f", "null", "NUL"
    ) -LogPath $loudnormPass1Log

    $statsJson = & $PythonExe -c "import json, pathlib, sys; sys.path.insert(0, r'$ScriptDir'); from voice_cleaner import extract_loudnorm_json; print(json.dumps(extract_loudnorm_json(pathlib.Path(r'$loudnormPass1Log').read_text(encoding='utf-8-sig')), ensure_ascii=False, indent=2))"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not parse loudnorm pass 1 output."
    }
    $loudnormStatsPath = Join-Path $WorkDir "loudnorm_premaster_pass1.json"
    ($statsJson | Out-String) | Set-Content -LiteralPath $loudnormStatsPath -Encoding UTF8

    $secondPassJson = & $PythonExe (Join-Path $ScriptDir "voice_cleaner.py") `
        "loudnorm-second-pass" `
        "--stats-json" $loudnormStatsPath `
        "--json"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not build loudnorm second pass filter."
    }
    $secondPassInfo = ($secondPassJson | Out-String) | ConvertFrom-Json
    $SecondPassFilter = [string]$secondPassInfo.filter

    Invoke-Checked -Command @(
        "ffmpeg", "-hide_banner", "-y", "-nostats",
        "-i", $PremasterFlac,
        "-af", $SecondPassFilter,
        "-c:a", "flac",
        "-sample_fmt", "s32",
        "-compression_level", "8",
        $CleanFlac
    ) -LogPath (Join-Path $WorkDir "voice_cleaner_clean_flac.txt") | Out-Null

    $sourceTrackArgs = @()
    $mkvInfoJson = & mkvmerge -J $InputVideo
    if ($LASTEXITCODE -eq 0) {
        $mkvInfo = ($mkvInfoJson | Out-String) | ConvertFrom-Json
        foreach ($track in $mkvInfo.tracks) {
            if ($track.type -eq "audio") {
                $sourceTrackArgs += @("--default-track-flag", "$($track.id)`:no")
                if ($track.id -eq $selectedAudioIndex) {
                    $sourceTrackArgs += @("--track-name", "$($track.id)`:$OriginalTitle")
                }
            }
        }
    }

    Invoke-Checked -Command @(
        @("mkvmerge", "--output", $OutputMkv) +
        $sourceTrackArgs +
        @(
            $InputVideo,
            "--language", "0:$cleanAudioLanguage",
            "--track-name", "0:$CleanTitle",
            "--default-track-flag", "0:yes",
            $CleanFlac
        )
    ) -LogPath (Join-Path $WorkDir "voice_cleaner_remux_mkv.txt") | Out-Null

    $finalProbe = Invoke-Checked -Command @(
        "ffprobe", "-hide_banner", "-show_format", "-show_streams", "-print_format", "json", $OutputMkv
    ) -LogPath (Join-Path $WorkDir "ffprobe_final.log")
    $finalProbe | Set-Content -LiteralPath (Join-Path $WorkDir "ffprobe_final.json") -Encoding UTF8

    if ($GenerateSamples) {
        if (!(Test-Path -LiteralPath $SamplesDir)) {
            New-Item -ItemType Directory -Path $SamplesDir | Out-Null
        }
        foreach ($sample in @(@(0, "00m00s"), @(600, "10m00s"))) {
            $seconds = [string]$sample[0]
            $label = [string]$sample[1]
            Invoke-Checked -Command @(
                "ffmpeg", "-hide_banner", "-y", "-nostats",
                "-ss", $seconds,
                "-t", "20",
                "-i", $InputVideo,
                "-map", "0:v:0",
                "-map", "0:$selectedAudioIndex",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "24",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                (Join-Path $SamplesDir "$label`_original.mp4")
            ) -LogPath (Join-Path $WorkDir "sample_$label`_original.txt") | Out-Null
            Invoke-Checked -Command @(
                "ffmpeg", "-hide_banner", "-y", "-nostats",
                "-ss", $seconds,
                "-t", "20",
                "-i", $InputVideo,
                "-i", $CleanFlac,
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "24",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                (Join-Path $SamplesDir "$label`_voice_cleaned.mp4")
            ) -LogPath (Join-Path $WorkDir "sample_$label`_voice_cleaned.txt") | Out-Null
        }
    }
}
finally {
    Pop-Location
}

if (!$KeepTemp -and (Test-Path -LiteralPath $PremasterFlac)) {
    Remove-Item -LiteralPath $PremasterFlac -Force
}

$report = @{
    workspace_id = $WorkspaceId
    input_video = $InputVideo
    selected_audio_stream = $selectedAudioIndex
    selected_audio_language = $selectedAudioLanguage
    clean_audio_language = $cleanAudioLanguage
    profile = $Profile
    model = $ModelPath
    clean_flac = $CleanFlac
    output_mkv = $OutputMkv
    kept_original_audio = $true
    clean_audio_default = $true
    max_output_container = $OutputFormat
    generated_samples = [bool]$GenerateSamples
}
Write-Report -Path $ReportPath -Payload $report

Write-Host "Done."
Write-Host "Clean FLAC: $CleanFlac"
Write-Host "MKV: $OutputMkv"
Write-Host "Report: $ReportPath"
