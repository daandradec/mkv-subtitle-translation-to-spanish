import unittest
from pathlib import Path


LAUNCHER = Path(__file__).resolve().parents[1] / "traducir_subs_mkv.ps1"


class PrepareResumeLauncherTests(unittest.TestCase):
    def test_source_extraction_precedes_translation_map_resolution(self):
        script = LAUNCHER.read_text(encoding="utf-8-sig")

        extraction = script.index('Write-Host "Extracting source subtitle stream')
        map_resolution = script.index(
            'if (!$PSBoundParameters.ContainsKey("TranslationJson"))'
        )
        self.assertLess(extraction, map_resolution)

    def test_missing_maps_emit_durable_checkpoint_and_exact_resume_context(self):
        script = LAUNCHER.read_text(encoding="utf-8-sig")

        self.assertIn(
            "mkv_subtitle_agentic_translation.workflow_checkpoint",
            script,
        )
        self.assertIn("[CHECKPOINT:AWAITING_TRANSLATION_MAPS]", script)
        self.assertIn('"--output-name", $OutputName', script)
        self.assertIn('"--stream-index", $SourceSubtitleStreamIndex', script)
        self.assertIn('"--mkv-track-id", $SourceMkvTrackId', script)
        self.assertIn("[CHECKPOINT:MISMATCH]", script)
        self.assertIn('"--source-language-override", $SourceLanguageOverride', script)
        self.assertIn('"--embedded-subtitle-format", $EmbeddedSubtitleFormat', script)
        self.assertIn('"--term-map-json", $termMapPath', script)

    def test_generated_subtitles_are_internal_debug_artifacts(self):
        script = LAUNCHER.read_text(encoding="utf-8-sig")

        self.assertIn(
            'Assert-PathInside -PathValue $SpanishAss -RequiredRoot $SubtitlesDir',
            script,
        )
        self.assertIn(
            'Assert-PathInside -PathValue $TvSafeSrt -RequiredRoot $SubtitlesDir',
            script,
        )
        self.assertIn(
            'Assert-PathInside -PathValue $NormalizationReport -RequiredRoot $ReportsDir',
            script,
        )

    def test_spanish_ass_is_first_subtitle_and_default_when_both_are_embedded(self):
        script = LAUNCHER.read_text(encoding="utf-8-sig")

        self.assertIn('$generatedSubtitleTrackOrder = if ($EmbeddedSubtitleFormat -eq "both")', script)
        self.assertIn('@("1:0", "2:0")', script)
        self.assertIn('--track-order $trackOrder', script)
        remux = script[script.index('Write-Host "Remuxing MKV'):]
        self.assertIn(
            '--track-name "0:$SpanishTitle" `\n'
            '            --default-track-flag 0:yes `\n'
            '            $SpanishAss',
            remux,
        )
        self.assertIn(
            '--track-name "0:$SpanishTitle TV-safe" `\n'
            '            --default-track-flag 0:no `\n'
            '            $TvSafeSrt',
            remux,
        )
        self.assertIn('$defaultSubtitleTracks.Count -ne 1', remux)
        self.assertIn('$defaultSubtitleTracks[0].id -ne $finalSubtitleTracks[0].id', remux)
        self.assertIn('Set-Content -LiteralPath $RemuxValidationReport', remux)


if __name__ == "__main__":
    unittest.main()
