import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from transcription_backend import build_backend_command, choose_backend, resolve_whisperx_decoding_options
from transcription_postprocess import language_metadata, postprocess_transcription
from transcription_workspace import build_transcription_workspace


def resolver_with(*names):
    available = set(names)
    return lambda name: f"C:/fake/{name}.exe" if name in available else None


class TranscriptionWorkflowTests(unittest.TestCase):
    def test_transcription_workspace_uses_shared_id_for_outputs(self):
        workspace = build_transcription_workspace("input/NIPPON SANGOKU.mp4", "NIPPON-SANGOKU-A1B2C3")
        self.assertEqual(workspace["workspace_id"], "NIPPON-SANGOKU-A1B2C3")
        self.assertIn("subtitle_work/NIPPON-SANGOKU-A1B2C3", workspace["audio_wav"].replace("\\", "/"))
        self.assertIn(
            "output/NIPPON-SANGOKU-A1B2C3/NIPPON SANGOKU.transcribed.srt",
            workspace["transcribed_srt"].replace("\\", "/"),
        )
        self.assertIn(
            "output/NIPPON-SANGOKU-A1B2C3/NIPPON SANGOKU.transcribed.mkv",
            workspace["transcribed_mkv"].replace("\\", "/"),
        )

    def test_backend_auto_prefers_whisperx(self):
        backend, warning = choose_backend("auto", resolver=resolver_with("whisperx", "whisper"))
        self.assertEqual(backend, "whisperx")
        self.assertEqual(warning, "")

    def test_backend_auto_falls_back_to_whisper_with_warning(self):
        backend, warning = choose_backend("auto", resolver=resolver_with("whisper"))
        self.assertEqual(backend, "whisper")
        self.assertIn("WhisperX no esta disponible", warning)

    def test_backend_auto_fails_without_any_backend(self):
        with self.assertRaises(RuntimeError):
            choose_backend("auto", resolver=resolver_with())

    def test_build_whisper_command_includes_transcribe_task(self):
        command = build_backend_command(
            backend="whisper",
            audio="audio.wav",
            output_dir="out",
            language="Spanish",
            whisper_model="turbo",
        )
        self.assertIn("--task", command)
        self.assertIn("transcribe", command)
        self.assertIn("--language", command)
        self.assertIn("Spanish", command)

    def test_build_whisperx_maximum_quality_command(self):
        command = build_backend_command(
            backend="whisperx",
            audio="audio.wav",
            output_dir="out",
            language="es",
            whisperx_quality="maximum",
            whisperx_initial_prompt="Clase virtual de auditoria.",
            whisperx_hotwords="DOFA, PESTEL",
        )
        self.assertEqual(command[command.index("--beam_size") + 1], "10")
        self.assertEqual(command[command.index("--patience") + 1], "2.0")
        self.assertEqual(command[command.index("--temperature") + 1], "0")
        self.assertEqual(command[command.index("--language") + 1], "es")
        self.assertIn("Clase virtual de auditoria.", command)
        self.assertIn("DOFA, PESTEL", command)

    def test_whisperx_quality_options_allow_explicit_overrides(self):
        options = resolve_whisperx_decoding_options("maximum", beam_size=8, patience=1.5)
        self.assertEqual(options, {"beam_size": 8, "patience": 1.5})

    def test_postprocess_generates_clean_srt_ass_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw"
            raw.mkdir()
            (raw / "audio.srt").write_text(
                "1\n00:00:01,000 --> 00:00:03,000\nHola <i>mundo</i>\n\n",
                encoding="utf-8",
            )
            (raw / "audio.json").write_text(json.dumps({"language": "es"}), encoding="utf-8")
            report = postprocess_transcription(
                raw_output_dir=raw,
                audio_stem="audio",
                output_srt=root / "final.srt",
                output_ass=root / "final.ass",
                report_path=root / "report.json",
                backend="whisper",
            )

            self.assertEqual(report["cue_count"], 1)
            self.assertEqual(report["mkv_language"], "spa")
            self.assertIn("Hola mundo", (root / "final.srt").read_text(encoding="utf-8"))
            self.assertIn("Dialogue: 0,0:00:01.00,0:00:03.00,Default", (root / "final.ass").read_text(encoding="utf-8"))

    def test_postprocess_rejects_empty_transcription(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw"
            raw.mkdir()
            (raw / "audio.srt").write_text("", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                postprocess_transcription(
                    raw_output_dir=raw,
                    audio_stem="audio",
                    output_srt=root / "final.srt",
                    output_ass=root / "final.ass",
                    report_path=root / "report.json",
                    backend="whisper",
                )

    def test_language_metadata_warns_for_non_translation_language(self):
        metadata = language_metadata("es")
        self.assertEqual(metadata["mkv_language"], "spa")
        self.assertEqual(metadata["language_display"], "Espa\u00f1ol")
        self.assertFalse(metadata["translation_supported"])
        self.assertIn("podria detenerse", metadata["translation_warning"])

    def test_postprocess_splits_long_cues_to_two_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw"
            raw.mkdir()
            long_text = (
                "uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince "
                "dieciseis diecisiete dieciocho diecinueve veinte"
            )
            (raw / "audio.srt").write_text(
                f"1\n00:00:01,000 --> 00:00:09,000\n{long_text}\n\n",
                encoding="utf-8",
            )
            (raw / "audio.json").write_text(json.dumps({"language": "es"}), encoding="utf-8")
            report = postprocess_transcription(
                raw_output_dir=raw,
                audio_stem="audio",
                output_srt=root / "final.srt",
                output_ass=root / "final.ass",
                report_path=root / "report.json",
                backend="whisper",
                max_line_chars=34,
                max_lines=2,
            )
            srt = (root / "final.srt").read_text(encoding="utf-8")
            blocks = [block for block in srt.strip().split("\n\n") if block.strip()]

            self.assertGreater(report["cue_count"], 1)
            for block in blocks:
                text_lines = block.splitlines()[2:]
                self.assertLessEqual(len(text_lines), 2)
                self.assertTrue(all(len(line) <= 34 or " " not in line for line in text_lines))


if __name__ == "__main__":
    unittest.main()
