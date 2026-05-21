param(
    [Alias("InputMkv")]
    [string]$InputVideo = "",
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
    [int]$MaxSubtitleLines = 2,
    [int]$MaxSubtitleLineChars = 52,
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
    $setupArgs = @(
        "-ProjectRoot", $ProjectRoot,
        "-Json"
    )
    if ($Device -eq "cuda") {
        $setupArgs += "-EnsureCudaTorch"
    }
    $envJson = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ScriptDir "init_python_env.ps1") `
        @setupArgs
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
            throw "No se encontro ningun archivo de video con audio soportado por FFmpeg/Whisper en la carpeta 'input'. Para transcribir audio, ubica un video en 'input/' o indica -InputVideo."
        }
        if ($candidates.Count -gt 1) {
            $names = ($candidates | ForEach-Object { $_.Name }) -join "', '"
            throw "Se encontraron multiples videos en 'input': '$names'. El flujo solo puede procesar un video por ejecucion. Indica exactamente un archivo con -InputVideo."
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
            return $resolved.Path
        }
    }

    throw "No se encontro el archivo de video indicado: $InputPath. Debe existir en 'input/' o debes pasar una ruta valida con -InputVideo."
}

function Assert-InputVideo {
    param([string]$InputPath)

    $probeJson = & ffprobe -v error `
        -show_entries stream=index,codec_type `
        -of json `
        $InputPath
    if ($LASTEXITCODE -ne 0) {
        throw "ffprobe no pudo inspeccionar el archivo de entrada. Verifica que sea un video soportado por FFmpeg/Whisper: $InputPath"
    }
    $probe = ($probeJson | Out-String) | ConvertFrom-Json
    $streams = @($probe.streams)
    $hasVideo = @($streams | Where-Object { $_.codec_type -eq "video" }).Count -gt 0
    $hasAudio = @($streams | Where-Object { $_.codec_type -eq "audio" }).Count -gt 0
    if (!$hasVideo) {
        throw "El archivo de entrada no contiene una pista de video: $InputPath"
    }
    if (!$hasAudio) {
        throw "El archivo de entrada no contiene pistas de audio para transcribir: $InputPath"
    }
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
        throw "No se encontraron pistas de audio en el video; no se puede transcribir."
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
            Write-Warning "Se encontraron multiples pistas de audio marcadas como default ($defaultIndexes). Se usara la primera segun el orden del contenedor. Indica -AudioStreamIndex para elegir otra."
        }
        return $defaultStreams[0]
    }
    return $streams[0]
}

function Resolve-WhisperLanguage {
    param(
        [string]$RequestedLanguage,
        $AudioStream
    )

    if (![string]::IsNullOrWhiteSpace($RequestedLanguage)) {
        return $RequestedLanguage
    }
    if (!$AudioStream -or !$AudioStream.tags -or !$AudioStream.tags.language) {
        return ""
    }
    $metadataLanguage = ([string]$AudioStream.tags.language).Trim().ToLowerInvariant()
    $languageMap = @{
        "eng" = "en"; "en" = "en"; "english" = "en"
        "fre" = "fr"; "fra" = "fr"; "fr" = "fr"; "french" = "fr"
        "jpn" = "ja"; "ja" = "ja"; "japanese" = "ja"
        "spa" = "es"; "es" = "es"; "spanish" = "es"
        "ger" = "de"; "deu" = "de"; "de" = "de"; "german" = "de"
        "por" = "pt"; "pt" = "pt"; "portuguese" = "pt"
        "ita" = "it"; "it" = "it"; "italian" = "it"
        "rus" = "ru"; "ru" = "ru"; "russian" = "ru"
        "kor" = "ko"; "ko" = "ko"; "korean" = "ko"
        "chi" = "zh"; "zho" = "zh"; "cmn" = "zh"; "zh" = "zh"; "chinese" = "zh"
        "hin" = "hi"; "hi" = "hi"; "hindi" = "hi"
    }
    if ($languageMap.ContainsKey($metadataLanguage)) {
        return [string]$languageMap[$metadataLanguage]
    }
    if ($metadataLanguage -and $metadataLanguage -ne "und") {
        return $metadataLanguage
    }
    return ""
}

$inputVideoWasProvided = $PSBoundParameters.ContainsKey("InputVideo") -or $PSBoundParameters.ContainsKey("InputMkv")
foreach ($commandName in @("ffmpeg", "ffprobe")) {
    if ($null -eq (Get-Command $commandName -ErrorAction SilentlyContinue)) {
        throw "$commandName not found in PATH."
    }
}
if (!$SkipRemux -and $null -eq (Get-Command "mkvmerge" -ErrorAction SilentlyContinue)) {
    throw "mkvmerge not found in PATH. Install MKVToolNix first, for example: choco install mkvtoolnix -y"
}

$InputVideo = Resolve-InputVideoPath -InputPath $InputVideo -WasProvided $inputVideoWasProvided
$PythonExe = Initialize-PythonEnvironment
Assert-InputVideo -InputPath $InputVideo

$workspaceArgs = @(
    (Join-Path $ScriptDir "transcription_workspace.py"),
    "--input-video", $InputVideo,
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

$selectedAudio = Select-AudioStream -InputPath $InputVideo -RequestedIndex $AudioStreamIndex
$selectedAudioIndex = [int]$selectedAudio.index
$EffectiveLanguage = Resolve-WhisperLanguage -RequestedLanguage $Language -AudioStream $selectedAudio

Write-Host "Workspace: $WorkspaceId"
Write-Host "Selected audio stream: 0:$selectedAudioIndex"
if ($EffectiveLanguage) {
    Write-Host "Transcription language: $EffectiveLanguage"
}

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
if ($EffectiveLanguage) {
    $backendArgs += @("--language", $EffectiveLanguage)
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
        -i $InputVideo `
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
    "--max-lines", ([string]$MaxSubtitleLines),
    "--max-line-chars", ([string]$MaxSubtitleLineChars),
    "--json"
)
if ($EffectiveLanguage) {
    $postprocessArgs += @("--requested-language", $EffectiveLanguage)
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
    Write-Host "Remuxing input video to MKV with transcribed subtitles..."
    $muxInput = $InputVideo
    $mkvInfoJson = & mkvmerge -J $muxInput
    if ($LASTEXITCODE -ne 0) {
        $intermediateMkv = Join-Path $SubtitleWorkDir "$([System.IO.Path]::GetFileNameWithoutExtension($InputVideo)).container.mkv"
        Write-Warning "mkvmerge could not inspect the original container directly. Creating an intermediate MKV with FFmpeg copy remux."
        Invoke-Checked {
            ffmpeg -y -v error `
                -i $InputVideo `
                -map 0 `
                -c copy `
                $intermediateMkv
        }
        $muxInput = $intermediateMkv
        $mkvInfoJson = & mkvmerge -J $muxInput
        if ($LASTEXITCODE -ne 0) {
            throw "Could not inspect input video or intermediate MKV with mkvmerge."
        }
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
            $muxInput `
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
