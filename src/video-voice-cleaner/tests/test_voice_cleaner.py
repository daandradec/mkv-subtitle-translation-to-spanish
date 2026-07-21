import json
import tempfile
import unittest
from pathlib import Path

from video_voice_cleaner.voice_cleaner import (
    build_voice_cleaner_workspace,
    extract_loudnorm_json,
    loudnorm_second_pass_filter,
    validate_profile,
    voice_filter_chain,
)


class VoiceCleanerTests(unittest.TestCase):
    def test_workspace_paths_share_output_name(self):
        workspace = build_voice_cleaner_workspace("input/capacitacion ma.mp4")
        self.assertEqual(workspace["output_name"], "capacitacion ma")
        self.assertIn("output/capacitacion ma/debug/video-voice-cleaner/work", workspace["work_dir"].replace("\\", "/"))
        self.assertIn("output/capacitacion ma/capacitacion ma.voice-cleaned.mkv", workspace["output_mkv"].replace("\\", "/"))
        self.assertIn("output/capacitacion ma/capacitacion ma.voice-cleaned.flac", workspace["clean_flac"].replace("\\", "/"))

    def test_profile_validation(self):
        self.assertEqual(validate_profile("conservative"), "conservative")
        with self.assertRaises(ValueError):
            validate_profile("robot")

    def test_filter_chain_includes_general_voice_filters(self):
        chain = voice_filter_chain("balanced", Path("models/voice-cleaner/std.rnnn"))
        self.assertIn("arnndn=m=models/voice-cleaner/std.rnnn:mix=0.35", chain)
        self.assertIn("afftdn=nr=8", chain)
        self.assertIn("deesser=", chain)
        self.assertIn("acompressor=", chain)
        self.assertNotIn("1281.5", chain)

    def test_asr_profile_is_stronger_than_conservative(self):
        conservative = voice_filter_chain("conservative", Path("models/voice-cleaner/std.rnnn"))
        asr = voice_filter_chain("asr", Path("models/voice-cleaner/std.rnnn"))
        self.assertIn("mix=0.25", conservative)
        self.assertIn("mix=0.45", asr)
        self.assertIn("afftdn=nr=11", asr)

    def test_extract_loudnorm_json(self):
        log = 'noise\n{"input_i":"-23.0","input_lra":"12.0","input_tp":"-1.5","input_thresh":"-34.0","target_offset":"1.0"}\n'
        stats = extract_loudnorm_json(log)
        self.assertEqual(stats["input_i"], "-23.0")

    def test_loudnorm_second_pass_filter(self):
        stats = {
            "input_i": "-23.0",
            "input_lra": "12.0",
            "input_tp": "-1.5",
            "input_thresh": "-34.0",
            "target_offset": "1.0",
        }
        result = loudnorm_second_pass_filter(stats)
        self.assertIn("measured_I=-23.0", result)
        self.assertIn("linear=true", result)

    def test_loudnorm_stats_round_trip_from_file_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stats.json"
            path.write_text(json.dumps({"input_i": "-20", "input_lra": "8", "input_tp": "-3", "input_thresh": "-30", "target_offset": "0"}), encoding="utf-8")
            stats = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("loudnorm=I=-16.0", loudnorm_second_pass_filter(stats))


if __name__ == "__main__":
    unittest.main()
