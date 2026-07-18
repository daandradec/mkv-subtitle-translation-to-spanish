param(
    [string]$InputPath = "",
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
    [int]$SectionSeconds = 180,
    [int]$ParagraphMaxChars = 900,
    [bool]$Fp16 = $true,
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
$ScriptDir = Split-Path -Parent $PSCommandPath
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$InputDir = Join-Path $ProjectRoot "input"

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

function Test-MediaWithAudio {
    param([string]$PathValue)
    $probeJson = & ffprobe -v error `
        -show_entries stream=index,codec_type `
        -of json `
        $PathValue
    if ($LASTEXITCODE -ne 0) {
        return $false
    }
    $probe = ($probeJson | Out-String) | ConvertFrom-Json
    $streams = @($probe.streams)
    $hasAudio = @($streams | Where-Object { $_.codec_type -eq "audio" }).Count -gt 0
    return $hasAudio
}

function Resolve-InputPath {
    param([string]$PathValue)
    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return ""
    }
    $candidatePaths = @()
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        $candidatePaths += $PathValue
    } else {
        $candidatePaths += (Join-Path $ProjectRoot $PathValue)
        $candidatePaths += (Join-Path $InputDir $PathValue)
    }
    foreach ($candidatePath in ($candidatePaths | Select-Object -Unique)) {
        if (Test-Path -LiteralPath $candidatePath) {
            return (Resolve-Path -LiteralPath $candidatePath).Path
        }
    }
    throw "No se encontro la entrada indicada: $PathValue. Debe ser un archivo de audio/video o una carpeta valida."
}

function Get-VideoInputs {
    param([string]$PathValue)
    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        if (!(Test-Path -LiteralPath $InputDir)) {
            throw "No existe la carpeta 'input'. Crea 'input/' y ubica alli un video, o indica -InputPath."
        }
        $files = @(Get-ChildItem -LiteralPath $InputDir -File | Sort-Object Name | Where-Object { Test-MediaWithAudio -PathValue $_.FullName })
        if ($files.Count -eq 0) {
            throw "No se encontro ningun archivo de audio/video con audio en 'input/'."
        }
        if ($files.Count -gt 1) {
            throw "Se encontraron multiples videos en 'input/'. Para procesarlos todos, llama el flujo con -InputPath '.\input'. Para uno solo, indica el archivo exacto."
        }
        return @($files[0].FullName)
    }

    $resolved = Resolve-InputPath -PathValue $PathValue
    $item = Get-Item -LiteralPath $resolved
    if ($item.PSIsContainer) {
        $files = @(Get-ChildItem -LiteralPath $item.FullName -File | Sort-Object Name | Where-Object { Test-MediaWithAudio -PathValue $_.FullName })
        if ($files.Count -eq 0) {
            throw "La carpeta indicada no contiene archivos de audio/video procesables: $resolved"
        }
        return @($files | ForEach-Object { $_.FullName })
    }

    if (!(Test-MediaWithAudio -PathValue $item.FullName)) {
        throw "El archivo indicado no contiene audio decodificable por FFmpeg/Whisper: $($item.FullName)"
    }
    return @($item.FullName)
}

function Select-AudioStream {
    param(
        [string]$VideoPath,
        [int]$RequestedIndex
    )

    $probeJson = & ffprobe -v error `
        -select_streams a `
        -show_entries stream=index:stream_disposition=default:stream_tags=language,title `
        -of json `
        $VideoPath
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudieron inspeccionar las pistas de audio con ffprobe."
    }
    $probe = ($probeJson | Out-String) | ConvertFrom-Json
    $streams = @($probe.streams)
    if ($streams.Count -eq 0) {
        throw "No se encontraron pistas de audio para transcribir."
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
        return $defaultStreams[0]
    }
    return $streams[0]
}

function Invoke-TextTranscriptionForVideo {
    param(
        [string]$VideoPath,
        [string]$PythonExe,
        [string]$RequestedWorkspaceId
    )

    $workspaceArgs = @(
        (Join-Path $ScriptDir "text_transcription_workspace.py"),
        "--input-video", $VideoPath,
        "--json"
    )
    if ($RequestedWorkspaceId) {
        $workspaceArgs += @("--workspace-id", $RequestedWorkspaceId)
    }
    $workspaceJson = & $PythonExe @workspaceArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Text transcription workspace path generation failed."
    }
    $workspaceInfo = ($workspaceJson | Out-String) | ConvertFrom-Json
    $workspaceId = [string]$workspaceInfo.workspace_id
    $textWorkDir = Resolve-ProjectPath ([string]$workspaceInfo.text_work_dir)
    $outputDir = Resolve-ProjectPath ([string]$workspaceInfo.output_dir)
    $audioWav = Resolve-ProjectPath ([string]$workspaceInfo.audio_wav)
    $audioStem = [string]$workspaceInfo.audio_stem
    $markdownPath = Resolve-ProjectPath ([string]$workspaceInfo.markdown)
    $reportPath = Resolve-ProjectPath ([string]$workspaceInfo.report)

    if ((Test-Path -LiteralPath $outputDir) -and !$Force -and $RequestedWorkspaceId) {
        throw "El output '$outputDir' ya existe. Usa -Force para reutilizar ese workspace o no pases -WorkspaceId para generar uno nuevo."
    }

    $selectedAudio = Select-AudioStream -VideoPath $VideoPath -RequestedIndex $AudioStreamIndex
    $selectedAudioIndex = [int]$selectedAudio.index

    $backendArgs = @(
        (Join-Path $ScriptDir "transcription_backend.py"),
        "--backend", $Backend,
        "--audio", $audioWav,
        "--output-dir", $outputDir,
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

    Write-Host "Workspace: $workspaceId"
    Write-Host "Input: $VideoPath"
    Write-Host "Selected audio stream: 0:$selectedAudioIndex"

    if ($DryRun) {
        Write-Host "Dry run; no audio extraction, transcription, or postprocess will be executed."
        Write-Host (($backendInfo.command | ForEach-Object { [string]$_ }) -join " ")
        return [pscustomobject][ordered]@{
            input = $VideoPath
            workspace_id = $workspaceId
            output_dir = $outputDir
            status = "dry-run"
        }
    }

    foreach ($directory in @($textWorkDir, $outputDir)) {
        if (!(Test-Path -LiteralPath $directory)) {
            New-Item -ItemType Directory -Path $directory | Out-Null
        }
    }

    Write-Host "Extracting audio to mono 16 kHz WAV..."
    Invoke-Checked {
        ffmpeg -y -v error `
            -i $VideoPath `
            -map "0:$selectedAudioIndex" `
            -vn `
            -ac 1 `
            -ar 16000 `
            -c:a pcm_s16le `
            $audioWav
    }

    Write-Host "Running text transcription backend: $($backendInfo.backend)"
    $command = @($backendInfo.command | ForEach-Object { [string]$_ })
    $executable = $command[0]
    $arguments = @()
    if ($command.Count -gt 1) {
        $arguments = $command[1..($command.Count - 1)]
    }
    Invoke-Checked { & $executable @arguments }

    Write-Host "Generating RAG-ready Markdown transcript..."
    $postprocessArgs = @(
        (Join-Path $ScriptDir "text_transcription_postprocess.py"),
        "--output-dir", $outputDir,
        "--audio-stem", $audioStem,
        "--video-stem", ([System.IO.Path]::GetFileNameWithoutExtension($VideoPath)),
        "--markdown", $markdownPath,
        "--report", $reportPath,
        "--source-video", $VideoPath,
        "--backend", ([string]$backendInfo.backend),
        "--audio-stream-index", ([string]$selectedAudioIndex),
        "--section-seconds", ([string]$SectionSeconds),
        "--paragraph-max-chars", ([string]$ParagraphMaxChars),
        "--json"
    )
    if ($Language) {
        $postprocessArgs += @("--requested-language", $Language)
    }
    $reportJson = & $PythonExe @postprocessArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Text transcription postprocess failed."
    }
    $reportInfo = ($reportJson | Out-String) | ConvertFrom-Json
    Write-Host "Markdown: $markdownPath"
    return [pscustomobject][ordered]@{
        input = $VideoPath
        workspace_id = $workspaceId
        output_dir = $outputDir
        markdown = $markdownPath
        backend = [string]$backendInfo.backend
        language = [string]$reportInfo.detected_language
        status = "ok"
    }
}

foreach ($commandName in @("ffmpeg", "ffprobe")) {
    if ($null -eq (Get-Command $commandName -ErrorAction SilentlyContinue)) {
        throw "$commandName not found in PATH."
    }
}

$PythonExe = Initialize-PythonEnvironment
$videos = Get-VideoInputs -PathValue $InputPath
if ($WorkspaceId -and $videos.Count -gt 1) {
    throw "-WorkspaceId solo se puede usar cuando se procesa un unico video. Para batch, deja que el flujo cree un workspace por video."
}

$results = New-Object System.Collections.ArrayList
$failures = New-Object System.Collections.ArrayList
foreach ($video in $videos) {
    try {
        [void]$results.Add((Invoke-TextTranscriptionForVideo -VideoPath $video -PythonExe $PythonExe -RequestedWorkspaceId $WorkspaceId))
    } catch {
        $failure = [pscustomobject][ordered]@{
            input = $video
            status = "failed"
            error = $_.Exception.Message
        }
        [void]$failures.Add($failure)
        Write-Warning "Fallo la transcripcion de '$video': $($_.Exception.Message)"
        if ($videos.Count -eq 1) {
            throw
        }
    }
}

Write-Host "Done."
Write-Host "Processed: $($results.Count); Failed: $($failures.Count)"
if ($failures.Count -gt 0) {
    $payload = [ordered]@{
        processed = $results
        failed = $failures
    }
    $payload | ConvertTo-Json -Depth 5 | Write-Host
    exit 1
}
