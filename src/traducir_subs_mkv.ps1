param(
    [string]$InputMkv = "",
    [int]$SourceSubtitleStreamIndex = 3,
    [int]$SourceMkvTrackId = 3,
    [string]$SourceLanguageOverride = "",
    [string]$EnglishAss = "subtitle_work\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].eng.ass",
    [string]$SpanishAss = "subtitle_work\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.ass",
    [string]$TvSafeSrt = "",
    [string]$NormalizationReport = "subtitle_work\spanish_normalization_report.json",
    [switch]$SkipSpanishNormalization,
    [ValidateSet("ass", "srt", "both")]
    [string]$EmbeddedSubtitleFormat = "both",
    [string]$OutputMkv = "Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.mkv",
    [string[]]$TranslationJson = @(
        "translations\translations_dialogue_part1.json",
        "translations\translations_dialogue_part2.json",
        "translations\translations_signs.json",
        "translations\translations_songs.json",
        "translations\translations_songs_extra.json"
    )
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $PSCommandPath
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
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
    "--stream-index", $SourceSubtitleStreamIndex,
    "--json"
)
if ($SourceLanguageOverride) {
    $languageArgs += @("--language-override", $SourceLanguageOverride)
}
$languageJson = & python $languageArgs
if ($LASTEXITCODE -ne 0) {
    throw "Source subtitle language validation failed."
}
$languageInfo = ($languageJson | Out-String) | ConvertFrom-Json
$SourceLanguage = [string]$languageInfo.source_language
Write-Host "Detected source language: $($languageInfo.source_language_name) ($SourceLanguage)"

if ($SourceLanguage -ne "en" -and !$PSBoundParameters.ContainsKey("TranslationJson")) {
    $videoStem = [System.IO.Path]::GetFileNameWithoutExtension($InputMkv)
    $safeVideoStem = ($videoStem -replace '[\\/:*?"<>|]', '_')
    $agenticTranslationDir = Join-Path "translations" (Join-Path $safeVideoStem $SourceLanguage)
    if (!(Test-Path -LiteralPath $agenticTranslationDir)) {
        New-Item -ItemType Directory -Path $agenticTranslationDir | Out-Null
    }
    $manifestPath = Join-Path $agenticTranslationDir "README.txt"
    @(
        "Source language '$SourceLanguage' is supported, but no translation maps were provided.",
        "Generate agentic translation JSON maps for this video in this folder, then rerun with -TranslationJson.",
        "Do not use the default English maps for this source language."
    ) | Set-Content -Path $manifestPath -Encoding UTF8
    throw "Supported non-English source language '$SourceLanguage' detected. Translation maps are required. Agentic workspace prepared at: $agenticTranslationDir"
}

Write-Host "Extracting source subtitle stream 0:$SourceSubtitleStreamIndex..."
Invoke-Checked { ffmpeg -y -v error -i $InputMkv -map "0:$SourceSubtitleStreamIndex" -c:s copy $EnglishAss }

$existingTranslationJson = @()
foreach ($path in $TranslationJson) {
    if (Test-Path -LiteralPath $path) {
        $existingTranslationJson += $path
    }
}

if ($existingTranslationJson.Count -eq 0) {
    throw "No translation JSON files found. Expected at least one of: $($TranslationJson -join ', ')"
}

Write-Host "Applying Spanish translations to ASS..."
Invoke-Checked {
    python (Join-Path $ScriptDir "ass_apply_translations.py") `
        --input-ass $EnglishAss `
        --output-ass $SpanishAss `
        --translations $existingTranslationJson `
        --blank-translated-english-fx
}

if ($TvSafeSrt) {
    Write-Host "Generating TV-safe Spanish SRT..."
    Invoke-Checked {
        python (Join-Path $ScriptDir "ass_to_tv_safe_srt.py") `
            --input-ass $SpanishAss `
            --output-srt $TvSafeSrt
    }
}

if ($TvSafeSrt -and !$SkipSpanishNormalization) {
    Write-Host "Normalizing Spanish ASS and TV-safe SRT..."
    Invoke-Checked {
        python (Join-Path $ScriptDir "normalize_spanish_subtitles.py") `
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

Write-Host "Remuxing MKV with MKVToolNix without re-encoding video/audio..."
Invoke-Checked {
    $mkvMergePath = if ($null -ne $MkvMergeCommand) { $MkvMergeCommand.Source } else { $LocalMkvMerge }
    if ($EmbeddedSubtitleFormat -eq "ass") {
        & $mkvMergePath `
            --output $OutputMkv `
            --default-track-flag "$SourceMkvTrackId`:no" `
            $InputMkv `
            --language 0:spa `
            --track-name "0:$SpanishTitle" `
            --default-track-flag 0:yes `
            $SpanishAss
    }
    elseif ($EmbeddedSubtitleFormat -eq "srt") {
        & $mkvMergePath `
            --output $OutputMkv `
            --default-track-flag "$SourceMkvTrackId`:no" `
            $InputMkv `
            --language 0:spa `
            --track-name "0:$SpanishTitle TV-safe" `
            --default-track-flag 0:yes `
            $TvSafeSrt
    }
    else {
        & $mkvMergePath `
            --output $OutputMkv `
            --default-track-flag "$SourceMkvTrackId`:no" `
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
