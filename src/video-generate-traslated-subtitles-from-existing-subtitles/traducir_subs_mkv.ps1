param(
    [string]$InputMkv = "",
    [int]$SourceSubtitleStreamIndex = -1,
    [int]$SourceMkvTrackId = -1,
    [string]$SourceLanguageOverride = "",
    [string]$EnglishAss = "",
    [string]$SpanishAss = "",
    [string]$TvSafeSrt = "",
    [string]$NormalizationReport = "",
    [switch]$SkipSpanishNormalization,
    [ValidateSet("ass", "srt", "both")]
    [string]$EmbeddedSubtitleFormat = "both",
    [string]$OutputMkv = "",
    [string[]]$TranslationJson = @(),
    [string[]]$TermMapJson = @(),
    [switch]$Resume
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $PSCommandPath
Import-Module (Join-Path $ScriptDir "..\..\scripts\lib\VideoToolkit.Infrastructure.psm1") -Force
$ProjectRuntime = Initialize-VideoToolProjectRuntime -SkillRoot $ScriptDir
$ProjectRoot = $ProjectRuntime.ProjectRoot
$ScriptsDir = $ProjectRuntime.ScriptsDir
$InputsDir = Join-Path $ProjectRoot "inputs"
$SpanishTitle = "Espa$([char]0x00F1)ol LatAm"
$MkvMergeCommand = Get-Command "mkvmerge" -ErrorAction SilentlyContinue

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
    $envJson = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ScriptsDir "manage_video_toolkit.ps1") `
        "setup-python-environment" `
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
    if (!(Test-Path -LiteralPath $InputsDir)) {
        return @()
    }
    return @(Get-ChildItem -LiteralPath $InputsDir -Filter "*.mkv" -File)
}

function Resolve-InputMkvPath {
    param(
        [string]$InputPath,
        [bool]$WasProvided
    )

    if (!$WasProvided -or [string]::IsNullOrWhiteSpace($InputPath)) {
        $candidates = Get-InputMkvCandidates
        if ($candidates.Count -eq 0) {
            throw "No se encontró ningún video MKV en la carpeta 'inputs'. Para ejecutar este flujo es obligatorio ubicar un archivo de video .mkv con subtítulos incrustados en 'inputs/' o indicar -InputMkv con la ruta del archivo."
        }
        if ($candidates.Count -gt 1) {
            $names = ($candidates | ForEach-Object { $_.Name }) -join "', '"
            throw "Se encontraron múltiples videos MKV en 'inputs': '$names'. El flujo solo puede procesar un video por ejecución. Indica exactamente un archivo con -InputMkv, por ejemplo: -InputMkv `"inputs\<nombre-del-video>.mkv`"."
        }
        return $candidates[0].FullName
    }

    $candidatePaths = @()
    if ([System.IO.Path]::IsPathRooted($InputPath)) {
        $candidatePaths += $InputPath
    } else {
        $candidatePaths += (Join-Path $InputsDir $InputPath)
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

    throw "No se encontró el archivo de video MKV indicado: $InputPath. Debe existir en 'inputs/' o debes pasar una ruta válida con -InputMkv."
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

function Assert-PathInside {
    param(
        [string]$PathValue,
        [string]$RequiredRoot,
        [string]$Label
    )
    $candidate = [System.IO.Path]::GetFullPath($PathValue)
    $root = [System.IO.Path]::GetFullPath($RequiredRoot).TrimEnd('\', '/')
    $prefix = $root + [System.IO.Path]::DirectorySeparatorChar
    if (!$candidate.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label must be generated inside '$root': $candidate"
    }
}

$workspaceArgs = @(
    "-m", "video_generate_traslated_subtitles_from_existing_subtitles.workspace",
    "--input-mkv", $InputMkv,
    "--json"
)
$workspaceJson = & $PythonExe @workspaceArgs
if ($LASTEXITCODE -ne 0) {
    throw "Workspace path generation failed."
}
$workspaceInfo = ($workspaceJson | Out-String) | ConvertFrom-Json
$OutputName = [string]$workspaceInfo.output_name
$OutputDir = Resolve-ProjectPath ([string]$workspaceInfo.output_dir)
$DebugDir = Resolve-ProjectPath ([string]$workspaceInfo.debug_dir)
$SubtitlesDir = Resolve-ProjectPath ([string]$workspaceInfo.subtitles_dir)
$ReportsDir = Resolve-ProjectPath ([string]$workspaceInfo.reports_dir)
$TranslationsWorkDir = Resolve-ProjectPath ([string]$workspaceInfo.translations_dir)
$TranslationCheckpoint = Resolve-ProjectPath ([string]$workspaceInfo.translation_checkpoint)
$CanonicalEnglishAss = Resolve-ProjectPath ([string]$workspaceInfo.source_ass)
$CanonicalSpanishAss = Resolve-ProjectPath ([string]$workspaceInfo.spanish_ass)
$CanonicalTvSafeSrt = Resolve-ProjectPath ([string]$workspaceInfo.tv_safe_srt)
$RemuxValidationReport = Resolve-ProjectPath ([string]$workspaceInfo.remux_validation_report)

if (!$EnglishAss) {
    $EnglishAss = $CanonicalEnglishAss
}
if (!$SpanishAss) {
    $SpanishAss = $CanonicalSpanishAss
}
if (!$TvSafeSrt) {
    $TvSafeSrt = $CanonicalTvSafeSrt
}
if (!$NormalizationReport) {
    $NormalizationReport = Resolve-ProjectPath ([string]$workspaceInfo.normalization_report)
}
if (!$OutputMkv) {
    $OutputMkv = Resolve-ProjectPath ([string]$workspaceInfo.output_mkv)
}

function Test-SameFullPath {
    param(
        [string]$First,
        [string]$Second
    )
    return [string]::Equals(
        [System.IO.Path]::GetFullPath($First),
        [System.IO.Path]::GetFullPath($Second),
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

$LegacySourceAss = Join-Path (Join-Path $DebugDir "source") (Split-Path -Leaf $CanonicalEnglishAss)
$LegacySidecarsDir = Join-Path $OutputDir "sidecars"
$LegacySpanishAss = Join-Path $LegacySidecarsDir (Split-Path -Leaf $CanonicalSpanishAss)
$LegacyTvSafeSrt = Join-Path $LegacySidecarsDir (Split-Path -Leaf $CanonicalTvSafeSrt)

if ($Resume) {
    if (Test-SameFullPath -First $EnglishAss -Second $LegacySourceAss) {
        $EnglishAss = $CanonicalEnglishAss
    }
    if (Test-SameFullPath -First $SpanishAss -Second $LegacySpanishAss) {
        $SpanishAss = $CanonicalSpanishAss
    }
    if (Test-SameFullPath -First $TvSafeSrt -Second $LegacyTvSafeSrt) {
        $TvSafeSrt = $CanonicalTvSafeSrt
    }
}

Assert-PathInside -PathValue $EnglishAss -RequiredRoot $SubtitlesDir -Label "Source subtitle"
Assert-PathInside -PathValue $NormalizationReport -RequiredRoot $ReportsDir -Label "Normalization report"
Assert-PathInside -PathValue $RemuxValidationReport -RequiredRoot $ReportsDir -Label "Remux validation report"
Assert-PathInside -PathValue $SpanishAss -RequiredRoot $SubtitlesDir -Label "Spanish ASS"
Assert-PathInside -PathValue $TvSafeSrt -RequiredRoot $SubtitlesDir -Label "TV-safe SRT"
Assert-PathInside -PathValue $OutputMkv -RequiredRoot $OutputDir -Label "Output MKV"

if ($null -eq $MkvMergeCommand) {
    throw "mkvmerge not found in PATH. Install MKVToolNix first, for example: choco install mkvtoolnix -y"
}

Write-Host "Validating source subtitle language..."
$languageArgs = @(
    "-m", "video_generate_traslated_subtitles_from_existing_subtitles.subtitle_language",
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
$SourceLanguageName = [string]$languageInfo.source_language_name
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

$null = Initialize-VideoOutputWorkspace `
    -ProjectRoot $ProjectRoot `
    -OutputDir $OutputDir `
    -DebugDir $DebugDir `
    -InputPath $InputMkv `
    -Workflow "video-generate-traslated-subtitles-from-existing-subtitles" `
    -Resume:$Resume

if ($Resume -and !(Test-Path -LiteralPath $TranslationCheckpoint -PathType Leaf)) {
    throw "[CHECKPOINT:MISSING] Cannot resume because the translation checkpoint does not exist: $TranslationCheckpoint"
}

foreach ($directory in @(
    $DebugDir,
    $SubtitlesDir,
    $ReportsDir,
    $TranslationsWorkDir,
    (Split-Path -Parent $TranslationCheckpoint),
    (Split-Path -Parent $EnglishAss),
    (Split-Path -Parent $SpanishAss),
    (Split-Path -Parent $TvSafeSrt),
    (Split-Path -Parent $NormalizationReport),
    (Split-Path -Parent $RemuxValidationReport)
)) {
    if ($directory -and !(Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
}

if ($Resume) {
    $legacySubtitleMoves = @(
        [pscustomobject]@{ Legacy = $LegacySourceAss; Canonical = $CanonicalEnglishAss }
        [pscustomobject]@{ Legacy = $LegacySpanishAss; Canonical = $CanonicalSpanishAss }
        [pscustomobject]@{ Legacy = $LegacyTvSafeSrt; Canonical = $CanonicalTvSafeSrt }
    )
    foreach ($legacyMove in $legacySubtitleMoves) {
        if (Test-Path -LiteralPath $legacyMove.Legacy -PathType Leaf) {
            if (Test-Path -LiteralPath $legacyMove.Canonical -PathType Leaf) {
                Remove-Item -LiteralPath $legacyMove.Legacy
            }
            else {
                Move-Item -LiteralPath $legacyMove.Legacy -Destination $legacyMove.Canonical
            }
        }
    }
    if ((Test-Path -LiteralPath $LegacySidecarsDir -PathType Container) -and
        @(Get-ChildItem -LiteralPath $LegacySidecarsDir -Force).Count -eq 0) {
        Remove-Item -LiteralPath $LegacySidecarsDir
    }
}

if (Test-Path -LiteralPath $TranslationCheckpoint -PathType Leaf) {
    try {
        $existingCheckpoint = Get-Content -LiteralPath $TranslationCheckpoint -Raw | ConvertFrom-Json
    }
    catch {
        throw "[CHECKPOINT:INVALID] Could not read existing workflow checkpoint: $TranslationCheckpoint"
    }

    if ([int]$existingCheckpoint.schema_version -ne 2) {
        throw "[CHECKPOINT:INVALID] Unsupported checkpoint schema in: $TranslationCheckpoint"
    }
    $checkpointInput = [System.IO.Path]::GetFullPath([string]$existingCheckpoint.input_mkv)
    $currentInput = [System.IO.Path]::GetFullPath($InputMkv)
    $sameInput = [string]::Equals(
        $checkpointInput,
        $currentInput,
        [System.StringComparison]::OrdinalIgnoreCase
    )
    $sameOutput = ([string]$existingCheckpoint.output_name -eq $OutputName)
    $sameLanguage = ([string]$existingCheckpoint.source_subtitle.language -eq $SourceLanguage)
    $sameStream = ([int]$existingCheckpoint.source_subtitle.ffprobe_stream_index -eq $SourceSubtitleStreamIndex)
    $sameTrack = ([int]$existingCheckpoint.source_subtitle.mkvmerge_track_id -eq $SourceMkvTrackId)
    if (!$sameOutput -or !$sameInput -or !$sameLanguage -or !$sameStream -or !$sameTrack) {
        throw "[CHECKPOINT:MISMATCH] Output '$OutputName' belongs to a different input, language, or subtitle track. Use its recorded -Resume command. Checkpoint: $TranslationCheckpoint"
    }
}

function Write-TranslationWorkflowCheckpoint {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("awaiting_translation_maps", "translation_maps_resolved", "completed")]
        [string]$Status
    )

    $checkpointArgs = @(
        "-m", "video_generate_traslated_subtitles_from_existing_subtitles.workflow_checkpoint",
        "--checkpoint", $TranslationCheckpoint,
        "--status", $Status,
        "--output-name", $OutputName,
        "--input-mkv", $InputMkv,
        "--source-ass", $EnglishAss,
        "--source-language", $SourceLanguage,
        "--source-language-name", $SourceLanguageName,
        "--source-codec", $SourceSubtitleCodec,
        "--stream-index", $SourceSubtitleStreamIndex,
        "--mkv-track-id", $SourceMkvTrackId,
        "--translations-dir", $TranslationsWorkDir,
        "--launcher", $PSCommandPath,
        "--spanish-ass", $SpanishAss,
        "--tv-safe-srt", $TvSafeSrt,
        "--normalization-report", $NormalizationReport,
        "--embedded-subtitle-format", $EmbeddedSubtitleFormat,
        "--output-mkv", $OutputMkv,
        "--json"
    )
    if ($SourceLanguageOverride) {
        $checkpointArgs += @("--source-language-override", $SourceLanguageOverride)
    }
    if ($SkipSpanishNormalization) {
        $checkpointArgs += "--skip-spanish-normalization"
    }
    foreach ($termMapPath in $TermMapJson) {
        $checkpointArgs += @("--term-map-json", $termMapPath)
    }

    $checkpointJson = & $PythonExe @checkpointArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Translation workflow checkpoint update failed."
    }
    return (($checkpointJson | Out-String) | ConvertFrom-Json)
}

Write-Host "Extracting source subtitle stream 0:$SourceSubtitleStreamIndex..."
if ($SourceSubtitleCodec -in @("ass", "ssa")) {
    Invoke-Checked { ffmpeg -y -v error -i $InputMkv -map "0:$SourceSubtitleStreamIndex" -c:s copy $EnglishAss }
}
elseif ($SourceSubtitleCodec -in @("subrip", "srt", "mov_text", "text")) {
    $sourceTextSubtitle = [System.IO.Path]::ChangeExtension($EnglishAss, ".srt")
    Invoke-Checked { ffmpeg -y -v error -i $InputMkv -map "0:$SourceSubtitleStreamIndex" -c:s srt $sourceTextSubtitle }
    Invoke-Checked {
        & $PythonExe -m video_toolkit.subtitles.text `
            --input $sourceTextSubtitle `
            --output $EnglishAss `
            --format srt
    }
}
elseif ($SourceSubtitleCodec -in @("webvtt", "vtt")) {
    $sourceTextSubtitle = [System.IO.Path]::ChangeExtension($EnglishAss, ".vtt")
    Invoke-Checked { ffmpeg -y -v error -i $InputMkv -map "0:$SourceSubtitleStreamIndex" -c:s webvtt $sourceTextSubtitle }
    Invoke-Checked {
        & $PythonExe -m video_toolkit.subtitles.text `
            --input $sourceTextSubtitle `
            --output $EnglishAss `
            --format vtt
    }
}
else {
    throw "Unsupported source subtitle codec for extraction: $SourceSubtitleCodec"
}

if (!$PSBoundParameters.ContainsKey("TranslationJson")) {
    $mapResolverArgs = @(
        "-m", "video_generate_traslated_subtitles_from_existing_subtitles.translation_maps",
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
    $checkpointInfo = Write-TranslationWorkflowCheckpoint -Status "awaiting_translation_maps"
    $resumeCommand = [string]$checkpointInfo.resume.command
    $manifestPath = Join-Path $agenticTranslationDir "README.txt"
    @(
        "Source language '$SourceLanguage' is supported, but no translation maps were provided.",
        "The source subtitle was extracted successfully to: $EnglishAss",
        "Generate translations_all.json or translations_*.json for this video in: $agenticTranslationDir",
        "Do not reuse maps from another video or workspace.",
        "Workflow checkpoint: $TranslationCheckpoint",
        "Resume this exact workspace with:",
        $resumeCommand
    ) | Set-Content -Path $manifestPath -Encoding UTF8
    throw "[CHECKPOINT:AWAITING_TRANSLATION_MAPS] Source subtitle extracted successfully, but translation maps are required. Checkpoint: $TranslationCheckpoint. Use the recorded -Resume command."
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

$null = Write-TranslationWorkflowCheckpoint -Status "translation_maps_resolved"

Write-Host "Normalizing and validating Spanish translation maps..."
$sanitizedTranslationDir = Join-Path $TranslationsWorkDir "sanitized"
$translationQualityReport = Join-Path $ReportsDir "translation_map_quality_report.json"
$sanitizedMapsJson = & $PythonExe -m video_generate_traslated_subtitles_from_existing_subtitles.normalize_translation_maps `
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
        & $PythonExe -m video_generate_traslated_subtitles_from_existing_subtitles.ass_apply_translations `
        --input-ass $EnglishAss `
        --output-ass $SpanishAss `
        --translations $existingTranslationJson `
        --blank-translated-english-fx `
        @termMapArgs
}

if ($TvSafeSrt) {
    Write-Host "Generating TV-safe Spanish SRT..."
    Invoke-Checked {
        & $PythonExe -m video_generate_traslated_subtitles_from_existing_subtitles.ass_to_tv_safe_srt `
            --input-ass $SpanishAss `
            --output-srt $TvSafeSrt
    }
}

if ($TvSafeSrt -and !$SkipSpanishNormalization) {
    Write-Host "Normalizing Spanish ASS and TV-safe SRT..."
    Invoke-Checked {
        & $PythonExe -m video_generate_traslated_subtitles_from_existing_subtitles.normalize_spanish_subtitles `
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

$mkvMergePath = $MkvMergeCommand.Source
$mkvInfoJson = & $mkvMergePath -J $InputMkv
if ($LASTEXITCODE -ne 0) {
    throw "Could not inspect input MKV with mkvmerge."
}
$mkvInfo = ($mkvInfoJson | Out-String) | ConvertFrom-Json
$sourceSubtitleDefaultArgs = @()
$originalNonSubtitleTrackOrder = @()
$originalSubtitleTrackOrder = @()
foreach ($track in $mkvInfo.tracks) {
    if ($track.type -eq "subtitles") {
        $sourceSubtitleDefaultArgs += @("--default-track-flag", "$($track.id)`:no")
        $originalSubtitleTrackOrder += "0:$($track.id)"
    }
    else {
        $originalNonSubtitleTrackOrder += "0:$($track.id)"
    }
}
if ($sourceSubtitleDefaultArgs.Count -eq 0) {
    $sourceSubtitleDefaultArgs += @("--default-track-flag", "$SourceMkvTrackId`:no")
}

$generatedSubtitleTrackOrder = if ($EmbeddedSubtitleFormat -eq "both") {
    @("1:0", "2:0")
}
else {
    @("1:0")
}
$trackOrder = @(
    $originalNonSubtitleTrackOrder
    $generatedSubtitleTrackOrder
    $originalSubtitleTrackOrder
) -join ","

Write-Host "Remuxing MKV with MKVToolNix without re-encoding video/audio..."
Invoke-Checked {
    if ($EmbeddedSubtitleFormat -eq "ass") {
        & $mkvMergePath `
            --output $OutputMkv `
            --track-order $trackOrder `
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
            --track-order $trackOrder `
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
            --track-order $trackOrder `
            @sourceSubtitleDefaultArgs `
            $InputMkv `
            --language 0:spa `
            --track-name "0:$SpanishTitle" `
            --default-track-flag 0:yes `
            $SpanishAss `
            --language 0:spa `
            --track-name "0:$SpanishTitle TV-safe" `
            --default-track-flag 0:no `
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

$finalMkvInfoJson = & $mkvMergePath -J $OutputMkv
if ($LASTEXITCODE -ne 0) {
    throw "Could not validate the remuxed MKV with mkvmerge."
}
$finalMkvInfo = ($finalMkvInfoJson | Out-String) | ConvertFrom-Json
$finalSubtitleTracks = @($finalMkvInfo.tracks | Where-Object { $_.type -eq "subtitles" })
$expectedPrimaryTitle = if ($EmbeddedSubtitleFormat -eq "srt") {
    "$SpanishTitle TV-safe"
}
else {
    $SpanishTitle
}
$validationErrors = @()
if ($finalSubtitleTracks.Count -eq 0) {
    $validationErrors += "The output MKV has no subtitle tracks."
}
else {
    $primaryTrack = $finalSubtitleTracks[0]
    if ([string]$primaryTrack.properties.language -ne "spa") {
        $validationErrors += "The first subtitle track language is not spa."
    }
    if ([string]$primaryTrack.properties.track_name -ne $expectedPrimaryTitle) {
        $validationErrors += "The first subtitle track is not '$expectedPrimaryTitle'."
    }
    if (!$primaryTrack.properties.default_track) {
        $validationErrors += "The first Spanish subtitle track is not marked default."
    }
}

$defaultSubtitleTracks = @($finalSubtitleTracks | Where-Object { $_.properties.default_track })
if ($defaultSubtitleTracks.Count -ne 1) {
    $validationErrors += "Expected exactly one default subtitle track, found $($defaultSubtitleTracks.Count)."
}
elseif ($finalSubtitleTracks.Count -gt 0 -and $defaultSubtitleTracks[0].id -ne $finalSubtitleTracks[0].id) {
    $validationErrors += "The default subtitle track is not the first subtitle track."
}

if ($EmbeddedSubtitleFormat -eq "both") {
    if ($finalSubtitleTracks.Count -lt 2) {
        $validationErrors += "Both subtitle formats were requested, but fewer than two subtitle tracks were generated."
    }
    else {
        $fallbackTrack = $finalSubtitleTracks[1]
        if ([string]$fallbackTrack.properties.language -ne "spa" -or
            [string]$fallbackTrack.properties.track_name -ne "$SpanishTitle TV-safe") {
            $validationErrors += "The second subtitle track is not the Spanish TV-safe fallback."
        }
        if ($fallbackTrack.properties.default_track) {
            $validationErrors += "The Spanish TV-safe fallback must not be default when ASS is embedded."
        }
    }
}

$actualSubtitleTracks = @($finalSubtitleTracks | ForEach-Object {
    [ordered]@{
        id = $_.id
        codec = $_.codec
        language = $_.properties.language
        title = $_.properties.track_name
        default = [bool]$_.properties.default_track
    }
})
[ordered]@{
    schema_version = 1
    status = if ($validationErrors.Count -eq 0) { "pass" } else { "fail" }
    output_mkv = [System.IO.Path]::GetFullPath($OutputMkv)
    expected_primary_title = $expectedPrimaryTitle
    subtitle_tracks = $actualSubtitleTracks
    errors = $validationErrors
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $RemuxValidationReport -Encoding UTF8

if ($validationErrors.Count -gt 0) {
    throw "Remuxed subtitle track validation failed. See report: $RemuxValidationReport"
}

$null = Write-TranslationWorkflowCheckpoint -Status "completed"
Write-Host "Done: $OutputMkv"
