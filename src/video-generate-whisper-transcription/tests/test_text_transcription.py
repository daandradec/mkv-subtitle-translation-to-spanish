import json
import tempfile
import unittest
from pathlib import Path

from video_generate_whisper_transcription.postprocess import clean_segment_text, postprocess_text_transcription, validate_markdown_paragraphs
from video_generate_whisper_transcription.workspace import build_text_transcription_workspace


class TextTranscriptionTests(unittest.TestCase):
    def test_workspace_uses_existing_pattern_and_outputs_markdown(self):
        workspace = build_text_transcription_workspace(
            "inputs/capacitacion ma.mp4",
        )
        self.assertEqual(workspace["output_name"], "capacitacion ma")
        self.assertIn("outputs/capacitacion ma/capacitacion ma.md", workspace["markdown"].replace("\\", "/"))
        self.assertIn("outputs/capacitacion ma/debug/video-generate-whisper-transcription/audio", workspace["audio_wav"].replace("\\", "/"))
        self.assertIn("outputs/capacitacion ma/debug/video-generate-whisper-transcription/whisper/raw", workspace["json"].replace("\\", "/"))
        self.assertIn("outputs/capacitacion ma/debug/video-generate-whisper-transcription/whisper/postprocess", workspace["vtt"].replace("\\", "/"))

    def test_workspace_reuses_deterministic_folder_name_when_it_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "output"
            (output_root / "video").mkdir(parents=True)
            workspace = build_text_transcription_workspace("inputs/video.mp4", output_root=output_root)
        self.assertEqual(workspace["output_name"], "video")

    def test_clean_segment_removes_boilerplate_and_repairs_spanish_question_mark(self):
        self.assertEqual(clean_segment_text("Subtitulos realizados por la comunidad", "es"), "")
        self.assertEqual(clean_segment_text("?Es esto una prueba?", "es"), "\u00bfEs esto una prueba?")
        self.assertEqual(
            clean_segment_text("la ciudad est\u00c3\u00a1 en caos \u00c2\u00bfen qu\u00c3\u00a9 zona?", "es"),
            "la ciudad est\u00e1 en caos \u00bfen qu\u00e9 zona?",
        )
        self.assertEqual(
            clean_segment_text(
                "No s\u00e9 por qu\u00e9 el se\u00f1or de Lugar, la se\u00f1ora Lugar me dej\u00f3 en un punto, pero no tengo ni idea d\u00f3nde me dej\u00f3.",
                "es",
            ),
            "No s\u00e9 por qu\u00e9 el se\u00f1or del lugar, la se\u00f1ora del lugar me dej\u00f3 en un punto. Pero no tengo ni idea d\u00f3nde me dej\u00f3.",
        )
        self.assertEqual(
            clean_segment_text("pues a m\u00ed no me dan porque yo perd\u00ed permiso en el trabajo", "es"),
            "pues a m\u00ed no me dan porque yo ped\u00ed permiso en el trabajo",
        )

    def test_verbatim_cleanup_preserves_recognized_words_and_repetitions(self):
        self.assertEqual(
            clean_segment_text("pues pues yo perd\u00ed permiso", "es", verbatim=True),
            "pues pues yo perd\u00ed permiso",
        )
        self.assertEqual(
            clean_segment_text("Subtitulos realizados por la comunidad", "es", verbatim=True),
            "Subtitulos realizados por la comunidad",
        )
        self.assertEqual(clean_segment_text("?Es esto una prueba?", "es", verbatim=True), "?Es esto una prueba?")

    def test_postprocess_generates_markdown_from_whisper_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "out"
            raw_output_dir = root / "debug" / "whisper" / "raw"
            debug_output_dir = root / "debug" / "whisper" / "postprocess"
            report_path = root / "debug" / "reports" / "text_transcription_report.json"
            output_dir.mkdir()
            raw_output_dir.mkdir(parents=True)
            payload = {
                "language": "es",
                "segments": [
                    {"start": 0.0, "end": 3.0, "text": "Hola hola equipo."},
                    {"start": 4.0, "end": 7.0, "text": "Este metodo mejora la trazabilidad del proceso."},
                    {"start": 190.0, "end": 195.0, "text": "Gracias por ver."},
                    {"start": 196.0, "end": 201.0, "text": "La decision de diseno prioriza resultados reproducibles."},
                ],
            }
            (raw_output_dir / "video.json").write_text(json.dumps(payload), encoding="utf-8")
            (raw_output_dir / "video.txt").write_text("raw transcript", encoding="utf-8")
            report = postprocess_text_transcription(
                output_dir=output_dir,
                debug_output_dir=debug_output_dir,
                raw_output_dir=raw_output_dir,
                audio_stem="video",
                video_stem="video",
                markdown_path=output_dir / "video.md",
                report_path=report_path,
                source_video="inputs/video.mp4",
                backend="whisperx",
                section_seconds=180,
            )
            markdown = (output_dir / "video.md").read_text(encoding="utf-8")
            srt = (output_dir / "video.srt").read_text(encoding="utf-8")
            vtt = (debug_output_dir / "video.vtt").read_text(encoding="utf-8")
            txt = (debug_output_dir / "video.txt").read_text(encoding="utf-8")
            self.assertEqual(report["detected_language"], "es")
            self.assertIn("srt", report["public_outputs"])
            self.assertIn("markdown", report["public_outputs"])
            self.assertIn("vtt", report["debug_outputs"])
            self.assertEqual(report["markdown_paragraph_count"], 2)
            self.assertEqual(report["markdown_alignment_warnings"], [])
            self.assertEqual(report["markdown_validation_warnings"], [])
            self.assertIn("## 00:00:00 - 00:00:07", markdown)
            self.assertIn("## 00:03:16 - 00:03:21", markdown)
            self.assertIn("Este metodo mejora la trazabilidad", markdown)
            self.assertIn("La decision de diseno prioriza", markdown)
            self.assertNotIn("Gracias por ver", markdown)
            self.assertIn("1\n00:00:00,000 --> 00:00:03,000", srt)
            self.assertIn("WEBVTT", vtt)
            self.assertIn("Este metodo mejora la trazabilidad", txt)
            self.assertTrue((raw_output_dir / "video.json").exists())
            self.assertFalse((output_dir / "video.json").exists())
            self.assertEqual(
                sorted(path.name for path in output_dir.iterdir() if path.is_file()),
                ["video.md", "video.srt"],
            )

    def test_postprocess_infers_spanish_when_backend_reports_english(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "out"
            output_dir.mkdir()
            payload = {
                "language": "en",
                "segments": [
                    {"start": 0.0, "end": 3.0, "text": "\u00bfEn qu\u00e9 zona est\u00e1s t\u00fa?"},
                    {"start": 4.0, "end": 8.0, "text": "Estoy en Bogot\u00e1 y la ciudad est\u00e1 en caos."},
                    {"start": 9.0, "end": 12.0, "text": "Ma\u00f1ana tenemos una sesi\u00f3n con la profe."},
                ],
            }
            (output_dir / "audio.json").write_text(json.dumps(payload), encoding="utf-8")
            report = postprocess_text_transcription(
                output_dir=output_dir,
                debug_output_dir=output_dir / "debug" / "postprocess",
                audio_stem="audio",
                video_stem="video",
                markdown_path=output_dir / "video.md",
                report_path=output_dir / "text_transcription_report.json",
                source_video="inputs/video.mp4",
                backend="whisperx",
            )
            self.assertEqual(report["detected_language"], "es")

    def test_postprocess_verbatim_preserves_duplicate_segments_and_records_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            payload = {
                "language": "es",
                "segments": [
                    {"start": 0.0, "end": 1.0, "text": "Hola hola."},
                    {"start": 1.1, "end": 2.0, "text": "Hola hola."},
                ],
            }
            (output_dir / "audio.json").write_text(json.dumps(payload), encoding="utf-8")
            report = postprocess_text_transcription(
                output_dir=output_dir,
                debug_output_dir=output_dir / "debug" / "postprocess",
                audio_stem="audio",
                video_stem="video",
                markdown_path=output_dir / "video.md",
                report_path=output_dir / "text_transcription_report.json",
                source_video="inputs/video.mp4",
                backend="whisperx",
                verbatim=True,
                backend_settings={"quality_profile": "maximum", "beam_size": 10},
                backend_versions={"whisperx": "3.8.5"},
                backend_command=["whisperx", "audio.wav"],
            )
            markdown = (output_dir / "video.md").read_text(encoding="utf-8")
            self.assertEqual(report["postprocess_mode"], "verbatim")
            self.assertEqual(report["clean_segment_count"], 2)
            self.assertEqual(report["removed_segment_count"], 0)
            self.assertEqual(report["backend_settings"]["beam_size"], 10)
            self.assertIn("postprocess_mode: 'verbatim'", markdown)
            self.assertIn("Hola hola. Hola hola.", markdown)

    def test_markdown_validation_detects_mojibake_and_time_regression(self):
        warnings = validate_markdown_paragraphs(
            [
                {"start": 10.0, "end": 11.0, "text": "Texto limpio"},
                {"start": 9.0, "end": 8.0, "text": "Texto con \u00c3 marcador"},
            ]
        )
        self.assertTrue(any("not monotonic" in warning for warning in warnings))
        self.assertTrue(any("ends before" in warning for warning in warnings))
        self.assertTrue(any("mojibake" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
