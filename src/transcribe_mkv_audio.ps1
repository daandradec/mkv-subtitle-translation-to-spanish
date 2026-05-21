param(
    [string]$InputMkv = "",
    [string]$WorkspaceId = "",
    [int]$AudioStreamIndex = -1,
    [string]$Language = "",
    [ValidateSet("auto", "whisperx", "whisper")]
    [string]$Backend = "auto",
    [string]$WhisperXModel = "large-v3",
    [string]$WhisperModel = "turbo",
    [string]$Device = "cuda",
    [string]$ComputeType = "float16",
    [int]$BatchSize = 8,
    [bool]$Fp16 = $true,
    [switch]$SkipRemux,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $PSCommandPath
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$InputDir = Join-Path $ProjectRoot "input"
$TranscriptionTitlePrefix = "Transcripci$([char]0x00F3)n"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
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

function Get-InputMkvCandidates {
    if (!(Test-Path -LiteralPath $InputDir)) {
        return @()
    }
    return @(Get-ChildItem -LiteralPath $InputDir -Filter "*.mkv" -File)
}

function Resolve-InputMkvPath {
    param(
        [string]$InputPath,
        [bool]$WasProvided
    )

    if (!$WasProvided -or [string]::IsNullOrWhiteSpace($InputPath)) {
        $candidates = Get-InputMkvCandidates
        if ($candidates.Count -eq 0) {
            throw "No se encontro ningun video MKV en la carpeta 'input'. Para transcribir audio, ubica un archivo .mkv en 'input/' o indica -InputMkv."
        }
        if ($candidates.Count -gt 1) {
            $names = ($candidates | ForEach-Object { $_.Name }) -join "', '"
            throw "Se encontraron multiples videos MKV en 'input': '$names'. El flujo solo puede procesar un video por ejecucion. Indica exactamente un archivo con -InputMkv."
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
            $resolved = Resolve-Path -LiteralPath $candidatePath
            if ([System.IO.Path]::GetExtension($resolved.Path).ToLowerInvariant() -ne ".mkv") {
                throw "El archivo de entrada debe ser un video MKV: $($resolved.Path)"
            }
            return $resolved.Path
        }
    }

    throw "No se encontro el archivo de video MKV indicado: $InputPath. Debe existir en 'input/' o debes pasar una ruta valida con -InputMkv."
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
        throw "Could not inspect audio streams with ffprobe."
    }
    $probe = ($probeJson | Out-String) | ConvertFrom-Json
    $streams = @($probe.streams)
    if ($streams.Count -eq 0) {
        throw "No se encontraron pistas de audio en el MKV; no se puede transcribir."
    }

    if ($RequestedIndex -ge 0) {
        foreach ($stream in $streams) {
            if ([int]$stream.index -eq $RequestedIndex) {
                return $stream
            }
        }
        throw "No se encontro la pista de audio con indice $RequestedIndex."
    }

    foreach ($stream in $streams) {
        if ($stream.disposition -and [int]$stream.disposition.default -eq 1) {
            return $stream
        }
    }
    return $streams[0]
}

$inputMkvWasProvided = $PSBoundParameters.ContainsKey("InputMkv")
$InputMkv = Resolve-InputMkvPath -InputPath $InputMkv -WasProvided $inputMkvWasProvided
$PythonExe = Initialize-PythonEnvironment

foreach ($commandName in @("ffmpeg", "ffprobe")) {
    if ($null -eq (Get-Command $commandName -ErrorAction SilentlyContinue)) {
        throw "$commandName not found in PATH."
    }
}
if (!$SkipRemux -and $null -eq (Get-Command "mkvmerge" -ErrorAction SilentlyContinue)) {
    throw "mkvmerge not found in PATH. Install MKVToolNix first, for example: choco install mkvtoolnix -y"
}

$workspaceArgs = @(
    (Join-Path $ScriptDir "transcription_workspace.py"),
    "--input-mkv", $InputMkv,
    "--json"
)
if ($WorkspaceId) {
    $workspaceArgs += @("--workspace-id", $WorkspaceId)
}
$workspaceJson = & $PythonExe @workspaceArgs
if ($LASTEXITCODE -ne 0) {
    throw "Transcription workspace path generation failed."
}
$workspaceInfo = ($workspaceJson | Out-String) | ConvertFrom-Json
$WorkspaceId = [string]$workspaceInfo.workspace_id
$SubtitleWorkDir = Resolve-ProjectPath ([string]$workspaceInfo.subtitle_work_dir)
$OutputDir = Resolve-ProjectPath ([string]$workspaceInfo.output_dir)
$WhisperOutputDir = Resolve-ProjectPath ([string]$workspaceInfo.whisper_output_dir)
$AudioWav = Resolve-ProjectPath ([string]$workspaceInfo.audio_wav)
$TranscribedSrt = Resolve-ProjectPath ([string]$workspaceInfo.transcribed_srt)
$TranscribedAss = Resolve-ProjectPath ([string]$workspaceInfo.transcribed_ass)
$TranscribedMkv = Resolve-ProjectPath ([string]$workspaceInfo.transcribed_mkv)
$TranscriptionReport = Resolve-ProjectPath ([string]$workspaceInfo.transcription_report)

$selectedAudio = Select-AudioStream -InputPath $InputMkv -RequestedIndex $AudioStreamIndex
$selectedAudioIndex = [int]$selectedAudio.index

Write-Host "Workspace: $WorkspaceId"
Write-Host "Selected audio stream: 0:$selectedAudioIndex"

$backendArgs = @(
    (Join-Path $ScriptDir "transcription_backend.py"),
    "--backend", $Backend,
    "--audio", $AudioWav,
    "--output-dir", $WhisperOutputDir,
    "--whisperx-model", $WhisperXModel,
    "--whisper-model", $WhisperModel,
    "--device", $Device,
    "--compute-type", $ComputeType,
    "--batch-size", $BatchSize,
    "--json"
)
if ($Language) {
    $backendArgs += @("--language", $Language)
}
if (!$Fp16) {
    $backendArgs += "--no-fp16"
}
$backendJson = & $PythonExe @backendArgs
if ($LASTEXITCODE -ne 0) {
    throw "Transcription backend resolution failed."
}
$backendInfo = ($backendJson | Out-String) | ConvertFrom-Json
if ($backendInfo.warning) {
    Write-Warning ([string]$backendInfo.warning)
}

if ($DryRun) {
    Write-Host "Dry run; no audio extraction, transcription, postprocess, or remux will be executed."
    Write-Host (($backendInfo.command | ForEach-Object { [string]$_ }) -join " ")
    exit 0
}

foreach ($directory in @($SubtitleWorkDir, $WhisperOutputDir, $OutputDir)) {
    if (!(Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory | Out-Null
    }
}

Write-Host "Extracting audio to mono 16 kHz WAV..."
Invoke-Checked {
    ffmpeg -y -v error `
        -i $InputMkv `
        -map "0:$selectedAudioIndex" `
        -vn `
        -ac 1 `
        -ar 16000 `
        -c:a pcm_s16le `
        $AudioWav
}

Write-Host "Running transcription backend: $($backendInfo.backend)"
$command = @($backendInfo.command | ForEach-Object { [string]$_ })
$executable = $command[0]
$arguments = @()
if ($command.Count -gt 1) {
    $arguments = $command[1..($command.Count - 1)]
}
$env:PYTHONIOENCODING = "utf-8"
Invoke-Checked { & $executable @arguments }

Write-Host "Postprocessing transcription outputs..."
$audioStem = [System.IO.Path]::GetFileNameWithoutExtension($AudioWav)
$postprocessArgs = @(
    (Join-Path $ScriptDir "transcription_postprocess.py"),
    "--raw-output-dir", $WhisperOutputDir,
    "--audio-stem", $audioStem,
    "--output-srt", $TranscribedSrt,
    "--output-ass", $TranscribedAss,
    "--report", $TranscriptionReport,
    "--backend", ([string]$backendInfo.backend),
    "--json"
)
if ($Language) {
    $postprocessArgs += @("--requested-language", $Language)
}
$postprocessJson = & $PythonExe @postprocessArgs
if ($LASTEXITCODE -ne 0) {
    throw "Transcription postprocess failed."
}
$reportInfo = ($postprocessJson | Out-String) | ConvertFrom-Json
if ($reportInfo.translation_warning) {
    Write-Warning ([string]$reportInfo.translation_warning)
}

if (!$SkipRemux) {
    Write-Host "Remuxing MKV with transcribed subtitles..."
    $mkvInfoJson = & mkvmerge -J $InputMkv
    if ($LASTEXITCODE -ne 0) {
        throw "Could not inspect input MKV with mkvmerge."
    }
    $mkvInfo = ($mkvInfoJson | Out-String) | ConvertFrom-Json
    $sourceSubtitleDefaultArgs = @()
    foreach ($track in $mkvInfo.tracks) {
        if ($track.type -eq "subtitles") {
            $sourceSubtitleDefaultArgs += @("--default-track-flag", "$($track.id)`:no")
        }
    }
    $languageDisplay = [string]$reportInfo.language_display
    if (!$languageDisplay) {
        $languageDisplay = "desconocido"
    }
    $subtitleTitle = "$TranscriptionTitlePrefix $languageDisplay"
    Invoke-Checked {
        mkvmerge `
            --output $TranscribedMkv `
            @sourceSubtitleDefaultArgs `
            $InputMkv `
            --language "0:$($reportInfo.mkv_language)" `
            --track-name "0:$subtitleTitle" `
            --default-track-flag 0:yes `
            $TranscribedSrt
    }

    Write-Host "Validating subtitle streams in output..."
    Invoke-Checked {
        ffprobe -v error `
            -select_streams s `
            -show_entries stream=index,codec_name:stream_disposition=default:stream_tags=language,title `
            -of json `
            $TranscribedMkv
    }
}

Write-Host "Done."
Write-Host "SRT: $TranscribedSrt"
Write-Host "ASS: $TranscribedAss"
if (!$SkipRemux) {
    Write-Host "MKV: $TranscribedMkv"
}
