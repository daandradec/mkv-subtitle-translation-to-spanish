param(
    [string]$InputMkv = "Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].mkv",
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
$SpanishTitle = "Espa$([char]0x00F1)ol LatAm"
$MkvMergeCommand = Get-Command "mkvmerge" -ErrorAction SilentlyContinue
$LocalMkvMerge = ".\tools\mkvtoolnix\mkvmerge.exe"

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

if (!(Test-Path -LiteralPath $InputMkv)) {
    throw "Input MKV not found: $InputMkv"
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

Write-Host "Extracting English ASS subtitle stream 0:3..."
Invoke-Checked { ffmpeg -y -v error -i $InputMkv -map 0:3 -c:s copy $EnglishAss }

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
    python ".\ass_apply_translations.py" `
        --input-ass $EnglishAss `
        --output-ass $SpanishAss `
        --translations $existingTranslationJson `
        --blank-translated-english-fx
}

if ($TvSafeSrt) {
    Write-Host "Generating TV-safe Spanish SRT..."
    Invoke-Checked {
        python ".\ass_to_tv_safe_srt.py" `
            --input-ass $SpanishAss `
            --output-srt $TvSafeSrt
    }
}

if ($TvSafeSrt -and !$SkipSpanishNormalization) {
    Write-Host "Normalizing Spanish ASS and TV-safe SRT..."
    Invoke-Checked {
        python ".\normalize_spanish_subtitles.py" `
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
            --default-track-flag 3:no `
            $InputMkv `
            --language 0:spa `
            --track-name "0:$SpanishTitle" `
            --default-track-flag 0:yes `
            $SpanishAss
    }
    elseif ($EmbeddedSubtitleFormat -eq "srt") {
        & $mkvMergePath `
            --output $OutputMkv `
            --default-track-flag 3:no `
            $InputMkv `
            --language 0:spa `
            --track-name "0:$SpanishTitle TV-safe" `
            --default-track-flag 0:yes `
            $TvSafeSrt
    }
    else {
        & $mkvMergePath `
            --output $OutputMkv `
            --default-track-flag 3:no `
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
