param(
    [string]$InputMkv = "Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].mkv",
    [string]$EnglishAss = "subtitle_work\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].eng.ass",
    [string]$SpanishAss = "subtitle_work\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.ass",
    [string]$OutputMkv = "Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.mkv",
    [string[]]$TranslationJson = @(
        "translations_dialogue_part1.json",
        "translations_dialogue_part2.json",
        "translations_signs.json",
        "translations_songs.json",
        "translations_songs_extra.json"
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

Write-Host "Remuxing MKV with MKVToolNix without re-encoding video/audio..."
Invoke-Checked {
    $mkvMergePath = if ($null -ne $MkvMergeCommand) { $MkvMergeCommand.Source } else { $LocalMkvMerge }
    & $mkvMergePath `
        --output $OutputMkv `
        --default-track-flag 3:no `
        $InputMkv `
        --language 0:spa `
        --track-name "0:$SpanishTitle" `
        --default-track-flag 0:yes `
        $SpanishAss
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
