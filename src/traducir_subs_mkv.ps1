param(
    [string]$InputMkv = "",
    [int]$SourceSubtitleStreamIndex = -1,
    [int]$SourceMkvTrackId = -1,
    [string]$SourceLanguageOverride = "",
    [string]$WorkspaceId = "",
    [string]$EnglishAss = "",
    [string]$SpanishAss = "",
    [string]$TvSafeSrt = "",
    [string]$NormalizationReport = "",
    [switch]$SkipSpanishNormalization,
    [ValidateSet("ass", "srt", "both")]
    [string]$EmbeddedSubtitleFormat = "both",
    [string]$OutputMkv = "",
    [string[]]$TranslationJson = @(),
    [string[]]$TermMapJson = @()
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $PSCommandPath
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$InputDir = Join-Path $ProjectRoot "input"
$SpanishTitle = "Espa$([char]0x00F1)ol LatAm"
$MkvMergeCommand = Get-Command "mkvmerge" -ErrorAction SilentlyContinue
$LocalMkvMerge = Join-Path $ProjectRoot "tools\mkvtoolnix\mkvmerge.exe"

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
            throw "No se encontró ningún video MKV en la carpeta 'input'. Para ejecutar este flujo es obligatorio ubicar un archivo de video .mkv con subtítulos incrustados en 'input/' o indicar -InputMkv con la ruta del archivo."
        }
        if ($candidates.Count -gt 1) {
            $names = ($candidates | ForEach-Object { $_.Name }) -join "', '"
            throw "Se encontraron múltiples videos MKV en 'input': '$names'. El flujo solo puede procesar un video por ejecución. Indica exactamente un archivo con -InputMkv, por ejemplo: -InputMkv `"input\<nombre-del-video>.mkv`"."
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

    throw "No se encontró el archivo de video MKV indicado: $InputPath. Debe existir en 'input/' o debes pasar una ruta válida con -InputMkv."
}

$inputMkvWasProvided = $PSBoundParameters.ContainsKey("InputMkv")
$InputMkv = Resolve-InputMkvPath -InputPath $InputMkv -WasProvided $inputMkvWasProvided

if ([System.IO.Path]::GetExtension($InputMkv).ToLowerInvariant() -ne ".mkv") {
    throw "El archivo de entrada debe ser un video MKV: $InputMkv"
}

$PythonExe = Initialize-PythonEnvironment

function Resolve-ProjectPath {
    param([string]$PathValue)
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return $PathValue
    }
    return (Join-Path $ProjectRoot $PathValue)
}

$workspaceArgs = @(
    (Join-Path $ScriptDir "subtitle_workspace.py"),
    "--input-mkv", $InputMkv,
    "--json"
)
if ($WorkspaceId) {
    $workspaceArgs += @("--workspace-id", $WorkspaceId)
}
$workspaceJson = & $PythonExe @workspaceArgs
if ($LASTEXITCODE -ne 0) {
    throw "Workspace path generation failed."
}
$workspaceInfo = ($workspaceJson | Out-String) | ConvertFrom-Json
$WorkspaceId = [string]$workspaceInfo.workspace_id
$SubtitleWorkDir = Resolve-ProjectPath ([string]$workspaceInfo.subtitle_work_dir)
$TranslationsWorkDir = Resolve-ProjectPath ([string]$workspaceInfo.translations_dir)
if (!(Test-Path -LiteralPath $SubtitleWorkDir)) {
    New-Item -ItemType Directory -Path $SubtitleWorkDir | Out-Null
}
if (!(Test-Path -LiteralPath $TranslationsWorkDir)) {
    New-Item -ItemType Directory -Path $TranslationsWorkDir | Out-Null
}

if (!$EnglishAss) {
    $EnglishAss = Resolve-ProjectPath ([string]$workspaceInfo.source_ass)
}
if (!$SpanishAss) {
    $SpanishAss = Resolve-ProjectPath ([string]$workspaceInfo.spanish_ass)
}
if (!$TvSafeSrt) {
    $TvSafeSrt = Resolve-ProjectPath ([string]$workspaceInfo.tv_safe_srt)
}
if (!$NormalizationReport) {
    $NormalizationReport = Resolve-ProjectPath ([string]$workspaceInfo.normalization_report)
}
if (!$OutputMkv) {
    $OutputMkv = Resolve-ProjectPath ([string]$workspaceInfo.output_mkv)
}

if ($null -eq $MkvMergeCommand -and !(Test-Path -LiteralPath $LocalMkvMerge)) {
    throw "mkvmerge not found in PATH or local tools folder. Install MKVToolNix first, for example: choco install mkvtoolnix -y"
}

foreach ($subtitlePath in @($EnglishAss, $SpanishAss)) {
    $subtitleDir = Split-Path -Parent $subtitlePath
    if ($subtitleDir -and !(Test-Path -LiteralPath $subtitleDir)) {
        New-Item -ItemType Directory -Path $subtitleDir | Out-Null
    }
}

if ($TvSafeSrt) {
    $tvSafeDir = Split-Path -Parent $TvSafeSrt
    if ($tvSafeDir -and !(Test-Path -LiteralPath $tvSafeDir)) {
        New-Item -ItemType Directory -Path $tvSafeDir | Out-Null
    }
}

if ($NormalizationReport) {
    $normalizationReportDir = Split-Path -Parent $NormalizationReport
    if ($normalizationReportDir -and !(Test-Path -LiteralPath $normalizationReportDir)) {
        New-Item -ItemType Directory -Path $normalizationReportDir | Out-Null
    }
}

Write-Host "Validating source subtitle language..."
$languageArgs = @(
    (Join-Path $ScriptDir "subtitle_language.py"),
    "--input-mkv", $InputMkv,
    "--json"
)
if ($SourceSubtitleStreamIndex -ge 0) {
    $languageArgs += @("--stream-index", $SourceSubtitleStreamIndex)
}
if ($SourceLanguageOverride) {
    $languageArgs += @("--language-override", $SourceLanguageOverride)
}
$languageJson = & $PythonExe @languageArgs
if ($LASTEXITCODE -ne 0) {
    throw "Source subtitle language validation failed."
}
$languageInfo = ($languageJson | Out-String) | ConvertFrom-Json
$SourceLanguage = [string]$languageInfo.source_language
$SourceSubtitleStreamIndex = [int]$languageInfo.stream_index
$SourceSubtitleCodec = ([string]$languageInfo.codec_name).ToLowerInvariant()
if ($SourceMkvTrackId -lt 0 -and $languageInfo.mkv_track_id -ne $null) {
    $SourceMkvTrackId = [int]$languageInfo.mkv_track_id
}
if ($SourceMkvTrackId -lt 0) {
    $SourceMkvTrackId = $SourceSubtitleStreamIndex
}
Write-Host "Detected source language: $($languageInfo.source_language_name) ($SourceLanguage)"
Write-Host "Selected subtitle stream: 0:$SourceSubtitleStreamIndex (mkvmerge track $SourceMkvTrackId)"

if (!$PSBoundParameters.ContainsKey("TranslationJson")) {
    $mapResolverArgs = @(
        (Join-Path $ScriptDir "translation_maps.py"),
        "--translations-dir", $TranslationsWorkDir,
        "--language", $SourceLanguage,
        "--json"
    )
    $resolvedMapsJson = & $PythonExe @mapResolverArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Translation map resolution failed."
    }
    $TranslationJson = @((($resolvedMapsJson | Out-String) | ConvertFrom-Json))
}

if ($TranslationJson.Count -eq 0) {
    $agenticTranslationDir = Join-Path $TranslationsWorkDir $SourceLanguage
    if (!(Test-Path -LiteralPath $agenticTranslationDir)) {
        New-Item -ItemType Directory -Path $agenticTranslationDir | Out-Null
    }
    $manifestPath = Join-Path $agenticTranslationDir "README.txt"
    @(
        "Source language '$SourceLanguage' is supported, but no translation maps were provided.",
        "Generate agentic translation JSON maps for this video in this folder, then rerun with -TranslationJson.",
        "Maps are resolved per workspace and per language for every source language, including English."
    ) | Set-Content -Path $manifestPath -Encoding UTF8
    throw "Supported source language '$SourceLanguage' detected, but translation maps are required. Agentic workspace prepared at: $agenticTranslationDir"
}

Write-Host "Extracting source subtitle stream 0:$SourceSubtitleStreamIndex..."
if ($SourceSubtitleCodec -in @("ass", "ssa")) {
    Invoke-Checked { ffmpeg -y -v error -i $InputMkv -map "0:$SourceSubtitleStreamIndex" -c:s copy $EnglishAss }
}
elseif ($SourceSubtitleCodec -in @("subrip", "srt", "mov_text", "text")) {
    $sourceTextSubtitle = [System.IO.Path]::ChangeExtension($EnglishAss, ".srt")
    Invoke-Checked { ffmpeg -y -v error -i $InputMkv -map "0:$SourceSubtitleStreamIndex" -c:s srt $sourceTextSubtitle }
    Invoke-Checked {
        & $PythonExe (Join-Path $ScriptDir "subtitle_text_to_ass.py") `
            --input $sourceTextSubtitle `
            --output $EnglishAss `
            --format srt
    }
}
elseif ($SourceSubtitleCodec -in @("webvtt", "vtt")) {
    $sourceTextSubtitle = [System.IO.Path]::ChangeExtension($EnglishAss, ".vtt")
    Invoke-Checked { ffmpeg -y -v error -i $InputMkv -map "0:$SourceSubtitleStreamIndex" -c:s webvtt $sourceTextSubtitle }
    Invoke-Checked {
        & $PythonExe (Join-Path $ScriptDir "subtitle_text_to_ass.py") `
            --input $sourceTextSubtitle `
            --output $EnglishAss `
            --format vtt
    }
}
else {
    throw "Unsupported source subtitle codec for extraction: $SourceSubtitleCodec"
}

$existingTranslationJson = @()
foreach ($path in $TranslationJson) {
    if (Test-Path -LiteralPath $path) {
        $existingTranslationJson += $path
    }
}

if ($existingTranslationJson.Count -eq 0) {
    throw "No translation JSON files found. Expected at least one of: $($TranslationJson -join ', ')"
}

Write-Host "Normalizing and validating Spanish translation maps..."
$sanitizedTranslationDir = Join-Path $SubtitleWorkDir "sanitized_translation_maps"
$translationQualityReport = Join-Path $SubtitleWorkDir "translation_map_quality_report.json"
$sanitizedMapsJson = & $PythonExe (Join-Path $ScriptDir "normalize_translation_maps.py") `
    --translations $existingTranslationJson `
    --output-dir $sanitizedTranslationDir `
    --report $translationQualityReport `
    --json
if ($LASTEXITCODE -ne 0) {
    throw "Translation map quality validation failed. See report: $translationQualityReport"
}
$sanitizedMapsInfo = ($sanitizedMapsJson | Out-String) | ConvertFrom-Json
$existingTranslationJson = @($sanitizedMapsInfo.translation_maps)

$existingTermMapJson = @()
foreach ($path in $TermMapJson) {
    if (Test-Path -LiteralPath $path) {
        $existingTermMapJson += $path
    }
}
$termMapArgs = @()
if ($existingTermMapJson.Count -gt 0) {
    $termMapArgs = @("--term-map") + $existingTermMapJson
}

Write-Host "Applying Spanish translations to ASS..."
Invoke-Checked {
        & $PythonExe (Join-Path $ScriptDir "ass_apply_translations.py") `
        --input-ass $EnglishAss `
        --output-ass $SpanishAss `
        --translations $existingTranslationJson `
        --blank-translated-english-fx `
        @termMapArgs
}

if ($TvSafeSrt) {
    Write-Host "Generating TV-safe Spanish SRT..."
    Invoke-Checked {
        & $PythonExe (Join-Path $ScriptDir "ass_to_tv_safe_srt.py") `
            --input-ass $SpanishAss `
            --output-srt $TvSafeSrt
    }
}

if ($TvSafeSrt -and !$SkipSpanishNormalization) {
    Write-Host "Normalizing Spanish ASS and TV-safe SRT..."
    Invoke-Checked {
        & $PythonExe (Join-Path $ScriptDir "normalize_spanish_subtitles.py") `
            --input-ass $SpanishAss `
            --input-srt $TvSafeSrt `
            --output-ass $SpanishAss `
            --output-srt $TvSafeSrt `
            --report $NormalizationReport
    }
}

$outputDir = Split-Path -Parent $OutputMkv
if ($outputDir -and !(Test-Path -LiteralPath $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

if ($EmbeddedSubtitleFormat -in @("srt", "both") -and !$TvSafeSrt) {
    throw "EmbeddedSubtitleFormat '$EmbeddedSubtitleFormat' requires -TvSafeSrt."
}

$mkvMergePath = if ($null -ne $MkvMergeCommand) { $MkvMergeCommand.Source } else { $LocalMkvMerge }
$mkvInfoJson = & $mkvMergePath -J $InputMkv
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
if ($sourceSubtitleDefaultArgs.Count -eq 0) {
    $sourceSubtitleDefaultArgs += @("--default-track-flag", "$SourceMkvTrackId`:no")
}

Write-Host "Remuxing MKV with MKVToolNix without re-encoding video/audio..."
Invoke-Checked {
    if ($EmbeddedSubtitleFormat -eq "ass") {
        & $mkvMergePath `
            --output $OutputMkv `
            @sourceSubtitleDefaultArgs `
            $InputMkv `
            --language 0:spa `
            --track-name "0:$SpanishTitle" `
            --default-track-flag 0:yes `
            $SpanishAss
    }
    elseif ($EmbeddedSubtitleFormat -eq "srt") {
        & $mkvMergePath `
            --output $OutputMkv `
            @sourceSubtitleDefaultArgs `
            $InputMkv `
            --language 0:spa `
            --track-name "0:$SpanishTitle TV-safe" `
            --default-track-flag 0:yes `
            $TvSafeSrt
    }
    else {
        & $mkvMergePath `
            --output $OutputMkv `
            @sourceSubtitleDefaultArgs `
            $InputMkv `
            --language 0:spa `
            --track-name "0:$SpanishTitle" `
            --default-track-flag 0:no `
            $SpanishAss `
            --language 0:spa `
            --track-name "0:$SpanishTitle TV-safe" `
            --default-track-flag 0:yes `
            $TvSafeSrt
    }
}

Write-Host "Validating subtitle streams in output..."
Invoke-Checked {
    ffprobe -v error `
        -select_streams s `
        -show_entries stream=index,codec_name:stream_disposition=default:stream_tags=language,title `
        -of json `
        $OutputMkv
}

Write-Host "Done: $OutputMkv"
