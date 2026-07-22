import unittest
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from video_generate_traslated_subtitles_from_existing_subtitles.workspace import build_workspace
from video_generate_traslated_subtitles_from_existing_subtitles.normalize_translation_maps import sanitize_map
from video_generate_traslated_subtitles_from_existing_subtitles.translation_maps import find_translation_maps
from video_generate_traslated_subtitles_from_existing_subtitles.translation_terms import apply_terms, load_term_maps
from video_generate_traslated_subtitles_from_existing_subtitles.workflow_checkpoint import (
    build_checkpoint,
    build_resume_command,
    write_checkpoint,
)


class WorkspaceAndTermsTests(unittest.TestCase):
    def test_workspace_paths_share_same_output_name(self):
        workspace = build_workspace("inputs/NIPPON SANGOKU.mkv")
        debug_dir = workspace["debug_dir"].replace("\\", "/")
        subtitles_dir = workspace["subtitles_dir"].replace("\\", "/")
        reports_dir = workspace["reports_dir"].replace("\\", "/")
        translations_dir = workspace["translations_dir"].replace("\\", "/")
        output_dir = workspace["output_dir"].replace("\\", "/")
        self.assertEqual(workspace["output_name"], "NIPPON SANGOKU")
        self.assertIn("outputs/NIPPON SANGOKU/debug/video-generate-traslated-subtitles-from-existing-subtitles", debug_dir)
        self.assertIn("outputs/NIPPON SANGOKU/debug/video-generate-traslated-subtitles-from-existing-subtitles/subtitles", subtitles_dir)
        self.assertIn("outputs/NIPPON SANGOKU/debug/video-generate-traslated-subtitles-from-existing-subtitles/reports", reports_dir)
        self.assertIn("outputs/NIPPON SANGOKU/debug/video-generate-traslated-subtitles-from-existing-subtitles/translations", translations_dir)
        self.assertEqual(output_dir, "outputs/NIPPON SANGOKU")
        self.assertIn("outputs/NIPPON SANGOKU/debug/video-generate-traslated-subtitles-from-existing-subtitles/subtitles/source/NIPPON SANGOKU.source.ass", workspace["source_ass"].replace("\\", "/"))
        self.assertIn("outputs/NIPPON SANGOKU/debug/video-generate-traslated-subtitles-from-existing-subtitles/subtitles/generated/NIPPON SANGOKU.spa.ass", workspace["spanish_ass"].replace("\\", "/"))
        self.assertIn("outputs/NIPPON SANGOKU/debug/video-generate-traslated-subtitles-from-existing-subtitles/subtitles/generated/NIPPON SANGOKU.spa.srt", workspace["tv_safe_srt"].replace("\\", "/"))
        self.assertIn("outputs/NIPPON SANGOKU/debug/video-generate-traslated-subtitles-from-existing-subtitles/reports/spanish_normalization_report.json", workspace["normalization_report"].replace("\\", "/"))
        self.assertIn("outputs/NIPPON SANGOKU/debug/video-generate-traslated-subtitles-from-existing-subtitles/reports/remux_validation_report.json", workspace["remux_validation_report"].replace("\\", "/"))
        self.assertIn("outputs/NIPPON SANGOKU/NIPPON SANGOKU.spa.mkv", workspace["output_mkv"].replace("\\", "/"))

    def test_default_term_map_normalizes_japanese_names(self):
        terms = load_term_maps([])
        text = "長尾武兎惇 ordenó avanzar hacia 金沢 y 大和."
        self.assertEqual(apply_terms(text, terms), "Nagao Buton ordenó avanzar hacia Kanazawa y Yamato.")

    def test_default_term_map_also_handles_mojibake_names(self):
        terms = load_term_maps([])
        text = "長尾武兎惇 ordenó avanzar hacia 金沢 y 大和."
        mojibake = text.encode("utf-8").decode("cp1252", errors="ignore")
        self.assertEqual(apply_terms(mojibake, terms), "Nagao Buton ordenÃ³ avanzar hacia Kanazawa y Yamato.")

    def test_translation_maps_resolve_per_workspace_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            language_dir = base / "en"
            language_dir.mkdir()
            first = language_dir / "translations_dialogue_part1.json"
            second = language_dir / "translations_songs.json"
            first.write_text('{"1":"Uno"}', encoding="utf-8")
            second.write_text('{"2":"Dos"}', encoding="utf-8")
            self.assertEqual(find_translation_maps(base, "en"), [first, second])

    def test_translation_maps_prefer_combined_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            language_dir = base / "ja"
            language_dir.mkdir()
            all_maps = language_dir / "translations_all.json"
            chunk = language_dir / "translations_chunk_01.json"
            all_maps.write_text('{"1":"Uno"}', encoding="utf-8")
            chunk.write_text('{"2":"Dos"}', encoding="utf-8")
            self.assertEqual(find_translation_maps(base, "ja"), [all_maps])

    def test_translation_map_sanitizer_repairs_mojibake_before_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "translations_all.json"
            output = root / "sanitized" / "translations_all.json"
            source.write_text(
                '{"16": "?Es... escrita de su mano! Demasi?ado sublime...", '
                '"17": "Esta guerra a?n est? en marcha."}',
                encoding="utf-8",
            )

            report = sanitize_map(source, output)
            data = json.loads(output.read_text(encoding="utf-8"))

            self.assertEqual(data["16"], "¡Es... escrita de su mano! Demasiado sublime...")
            self.assertEqual(data["17"], "Esta guerra aún está en marcha.")
            self.assertEqual(report["suspicious_question_replacement_count"], 0)

    def test_translation_checkpoint_records_exact_resume_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_mkv = root / "input" / "Movie.mkv"
            debug_dir = root / "output" / "Movie" / "debug" / "video-generate-traslated-subtitles-from-existing-subtitles"
            source_ass = debug_dir / "source" / "Movie.source.ass"
            translations_dir = debug_dir / "translations"
            launcher = root / "src" / "video-generate-traslated-subtitles-from-existing-subtitles" / "traducir_subs_mkv.ps1"
            payload = build_checkpoint(
                status="awaiting_translation_maps",
                output_name="Movie",
                input_mkv=input_mkv,
                source_ass=source_ass,
                source_language="en",
                source_language_name="English",
                source_codec="ass",
                stream_index=3,
                mkv_track_id=4,
                translations_dir=translations_dir,
                launcher=launcher,
            )

            self.assertEqual(payload["output_name"], "Movie")
            self.assertEqual(payload["source_subtitle"]["ffprobe_stream_index"], 3)
            self.assertEqual(payload["source_subtitle"]["mkvmerge_track_id"], 4)
            self.assertEqual(
                payload["translation_maps"]["preferred_file"],
                str((translations_dir / "en" / "translations_all.json").resolve()),
            )
            self.assertIn("-Resume", payload["resume"]["command"])
            self.assertIn("-SourceSubtitleStreamIndex 3", payload["resume"]["command"])

    def test_resume_command_preserves_effective_options_and_quotes_arrays(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Director's Cut"
            command = build_resume_command(
                root / "traducir_subs_mkv.ps1",
                root / "Movie's Cut.mkv",
                3,
                4,
                source_language_override="en",
                source_ass=root / "Movie.source.ass",
                spanish_ass=root / "Movie.spa.ass",
                tv_safe_srt=root / "Movie.spa.srt",
                normalization_report=root / "normalization.json",
                skip_spanish_normalization=True,
                embedded_subtitle_format="srt",
                output_mkv=root / "Movie.spa.mkv",
                term_map_json=(root / "terms one.json", root / "terms two.json"),
            )

            self.assertIn("-SourceLanguageOverride 'en'", command)
            self.assertIn("-EmbeddedSubtitleFormat 'srt'", command)
            self.assertIn("-SkipSpanishNormalization", command)
            self.assertIn("Director''s Cut", command)
            self.assertIn("Movie''s Cut.mkv", command)
            self.assertIn("-TermMapJson @(", command)
            self.assertIn("terms one.json", command)
            self.assertIn("terms two.json", command)
            self.assertTrue(command.startswith("& '"))

    @unittest.skipUnless(shutil.which("powershell"), "Windows PowerShell is required")
    def test_resume_command_binds_multiple_term_maps_as_one_array(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            probe = root / "argument probe.ps1"
            probe.write_text(
                """param(
[string]$InputMkv,
[switch]$Resume,
    [int]$SourceSubtitleStreamIndex,
    [int]$SourceMkvTrackId,
    [string]$EnglishAss,
    [string]$EmbeddedSubtitleFormat,
    [string[]]$TermMapJson
)
[pscustomobject]@{
    Resume = [bool]$Resume
    StreamIndex = $SourceSubtitleStreamIndex
    TermMapCount = $TermMapJson.Count
    FirstTermMap = $TermMapJson[0]
    SecondTermMap = $TermMapJson[1]
} | ConvertTo-Json -Compress
""",
                encoding="utf-8-sig",
            )
            first_term = root / "terms one.json"
            second_term = root / "Director's terms.json"
            command = build_resume_command(
                probe,
                root / "Movie.mkv",
                3,
                4,
                source_ass=root / "Movie.source.ass",
                term_map_json=(first_term, second_term),
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["Resume"])
            self.assertEqual(payload["StreamIndex"], 3)
            self.assertEqual(payload["TermMapCount"], 2)
            self.assertEqual(payload["FirstTermMap"], str(first_term.resolve()))
            self.assertEqual(payload["SecondTermMap"], str(second_term.resolve()))

    def test_translation_checkpoint_preserves_creation_time_across_status_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / "translation_checkpoint.json"
            values = {
                "output_name": "Movie",
                "input_mkv": root / "input" / "Movie.mkv",
                "source_ass": root / "output" / "Movie" / "debug" / "video-generate-traslated-subtitles-from-existing-subtitles" / "source" / "Movie.source.ass",
                "source_language": "en",
                "source_language_name": "English",
                "source_codec": "ass",
                "stream_index": 3,
                "mkv_track_id": 4,
                "translations_dir": root / "output" / "Movie" / "debug" / "video-generate-traslated-subtitles-from-existing-subtitles" / "translations",
                "launcher": root / "src" / "video-generate-traslated-subtitles-from-existing-subtitles" / "traducir_subs_mkv.ps1",
            }
            first = write_checkpoint(
                checkpoint,
                status="awaiting_translation_maps",
                **values,
            )
            second = write_checkpoint(
                checkpoint,
                status="translation_maps_resolved",
                **values,
            )
            completed = write_checkpoint(
                checkpoint,
                status="completed",
                **values,
            )

            self.assertEqual(second["status"], "translation_maps_resolved")
            self.assertEqual(second["created_at_utc"], first["created_at_utc"])
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["created_at_utc"], first["created_at_utc"])
            saved = json.loads(checkpoint.read_text(encoding="utf-8-sig"))
            self.assertEqual(saved["status"], "completed")


if __name__ == "__main__":
    unittest.main()
