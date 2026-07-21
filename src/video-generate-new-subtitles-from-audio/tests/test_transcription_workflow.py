import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_toolkit.subtitles.text import ms_to_ass_time
from video_generate_new_subtitles_from_audio.postprocess import language_metadata, postprocess_transcription
from video_generate_new_subtitles_from_audio.remux import (
    build_ffmpeg_remux_command,
    export_synchronized_ass,
    parse_srt_start_times,
    remux_strategy,
    remux_transcription,
)
from video_generate_new_subtitles_from_audio.workspace import build_transcription_workspace


class TranscriptionWorkflowTests(unittest.TestCase):
    def test_transcription_workspace_uses_deterministic_output_name(self):
        workspace = build_transcription_workspace("input/NIPPON SANGOKU.mp4")
        self.assertEqual(workspace["output_name"], "NIPPON SANGOKU")
        self.assertIn("output/NIPPON SANGOKU/debug/video-generate-new-subtitles-from-audio/audio", workspace["audio_wav"].replace("\\", "/"))
        self.assertIn(
            "output/NIPPON SANGOKU/debug/video-generate-new-subtitles-from-audio/postprocess/NIPPON SANGOKU.transcribed.srt",
            workspace["transcribed_srt"].replace("\\", "/"),
        )
        self.assertIn(
            "output/NIPPON SANGOKU/NIPPON SANGOKU.transcribed.mkv",
            workspace["transcribed_mkv"].replace("\\", "/"),
        )
        self.assertIn(
            "output/NIPPON SANGOKU/sidecars/NIPPON SANGOKU.transcribed.ass",
            workspace["exported_ass"].replace("\\", "/"),
        )
        self.assertNotEqual(
            Path(workspace["transcribed_mkv"]).parent,
            Path(workspace["exported_ass"]).parent,
        )
        self.assertNotEqual(
            Path(workspace["transcribed_mkv"]).parent,
            Path(workspace["transcribed_srt"]).parent,
        )
        self.assertIn(
            "output/NIPPON SANGOKU/debug/video-generate-new-subtitles-from-audio/reports/remux_validation.json",
            workspace["remux_validation_report"].replace("\\", "/"),
        )

    def test_postprocess_generates_internal_clean_srt_without_ass_by_default(self):
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
                report_path=root / "report.json",
                backend="whisper",
            )

            self.assertEqual(report["cue_count"], 1)
            self.assertEqual(report["mkv_language"], "spa")
            self.assertIn("Hola mundo", (root / "final.srt").read_text(encoding="utf-8"))
            self.assertFalse((root / "final.ass").exists())

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
                    report_path=root / "report.json",
                    backend="whisper",
                )

    def test_language_metadata_warns_for_non_translation_language(self):
        metadata = language_metadata("es")
        self.assertEqual(metadata["mkv_language"], "spa")
        self.assertEqual(metadata["language_display"], "Español")
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

    def test_remux_strategy_uses_shared_timeline_outside_matroska(self):
        self.assertEqual(remux_strategy("matroska,webm"), "mkvmerge-native")
        self.assertEqual(remux_strategy("mov,mp4,m4a,3gp,3g2,mj2"), "ffmpeg-shared-timeline")
        self.assertEqual(remux_strategy("avi"), "ffmpeg-shared-timeline")

    def test_ffmpeg_remux_command_has_no_manual_delay_or_trim(self):
        command = build_ffmpeg_remux_command(
            "input.mp4",
            "transcription.srt",
            "output.mkv",
            "spa",
            "Transcripción Español",
            source_subtitle_count=2,
        )
        self.assertEqual(command.count("-i"), 2)
        self.assertIn("1:0", command)
        self.assertNotIn("-ss", command)
        self.assertNotIn("--sync", command)
        self.assertIn("-disposition:s:0", command)
        self.assertIn("-disposition:s:1", command)
        self.assertIn("-disposition:s:2", command)

    def test_parse_srt_start_times(self):
        with tempfile.TemporaryDirectory() as tmp:
            srt = Path(tmp) / "sample.srt"
            srt.write_text(
                "1\n00:00:04,785 --> 00:00:06,426\nHola\n\n"
                "2\n01:02:03,004 --> 01:02:04,000\nMundo\n\n",
                encoding="utf-8",
            )
            self.assertEqual(parse_srt_start_times(srt), [4.785, 3723.004])

    def test_ass_export_rejects_a_sidecar_beside_the_mkv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(RuntimeError, "separate sidecars directory"):
                export_synchronized_ass(root / "video.mkv", root / "video.ass", 2, "Transcription")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg tools are required")
    def test_ffmpeg_shared_timeline_preserves_sync_for_mp4_edit_list(self):
        def run(command):
            return subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")

        def first_non_silence(path):
            completed = subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "info",
                    "-i",
                    str(path),
                    "-map",
                    "0:a:0",
                    "-af",
                    "silencedetect=noise=-35dB:d=0.3",
                    "-f",
                    "null",
                    "NUL" if Path.cwd().drive else "/dev/null",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            match = re.search(r"silence_end:\s*([0-9.]+)", completed.stderr)
            if not match:
                raise AssertionError(f"Could not detect the first non-silent sample:\n{completed.stderr}")
            return float(match.group(1))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base.mp4"
            edited = root / "edited.mp4"
            srt = root / "transcription.srt"
            output = root / "output.mkv"
            exported_ass = root / "sidecars" / "output.ass"
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=160x90:r=24:d=12",
                    "-f",
                    "lavfi",
                    "-i",
                    r"aevalsrc=if(gte(t\,7.4)\,0.8*sin(2*PI*440*t)\,0):s=48000:d=12",
                    "-c:v",
                    "mpeg4",
                    "-g",
                    "120",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(base),
                ]
            )
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-ss",
                    "2.67",
                    "-i",
                    str(base),
                    "-t",
                    "8",
                    "-c",
                    "copy",
                    str(edited),
                ]
            )
            srt.write_text(
                "1\n00:00:04,785 --> 00:00:06,426\nPrueba de sincronización.\n\n",
                encoding="utf-8",
            )

            report = remux_transcription(
                edited,
                srt,
                output,
                "spa",
                "Transcripción Español",
                export_ass_path=exported_ass,
            )
            packet_probe = json.loads(
                run(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-select_streams",
                        str(report["subtitle_stream_index"]),
                        "-show_packets",
                        "-show_entries",
                        "packet=pts_time",
                        "-of",
                        "json",
                        str(output),
                    ]
                ).stdout
            )
            embedded_cue = float(packet_probe["packets"][0]["pts_time"])
            source_delta = 4.785 - first_non_silence(edited)
            output_delta = embedded_cue - first_non_silence(output)

            self.assertEqual(report["strategy"], "ffmpeg-shared-timeline")
            self.assertLess(abs(output_delta - source_delta), 0.08)
            self.assertLessEqual(report["timeline_shift_spread_seconds"], 0.005)
            self.assertEqual(report["ass_export"]["status"], "pass")
            self.assertEqual(report["ass_export"]["cue_count"], 1)
            self.assertAlmostEqual(report["ass_export"]["first_cue_seconds"], embedded_cue, places=3)
            self.assertTrue(exported_ass.exists())
            expected_ass_start = ms_to_ass_time(round(embedded_cue * 1000))
            self.assertIn(f"Dialogue: 0,{expected_ass_start}", exported_ass.read_text(encoding="utf-8"))
            self.assertFalse(output.with_suffix(".srt").exists())
            self.assertFalse(output.with_suffix(".ass").exists())


if __name__ == "__main__":
    unittest.main()
