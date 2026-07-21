import importlib.util
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DETECTOR_PATH = (
    REPOSITORY_ROOT
    / ".agents"
    / "skills"
    / "video-text-agent-transcription"
    / "scripts"
    / "detect_language.py"
)
SPEC = importlib.util.spec_from_file_location("video_text_language_detector", DETECTOR_PATH)
DETECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DETECTOR)


class LanguageDetectionTests(unittest.TestCase):
    def test_select_audio_stream_prefers_default(self):
        streams = [
            {"index": 1, "disposition": {"default": 0}},
            {"index": 3, "disposition": {"default": 1}},
        ]
        self.assertEqual(DETECTOR.select_audio_stream(streams), 3)

    def test_select_audio_stream_honors_explicit_index(self):
        streams = [{"index": 1}, {"index": 3}]
        self.assertEqual(DETECTOR.select_audio_stream(streams, requested_index=1), 1)
        with self.assertRaises(RuntimeError):
            DETECTOR.select_audio_stream(streams, requested_index=9)

    def test_probe_offsets_cover_early_middle_and_late_audio(self):
        self.assertEqual(DETECTOR.build_probe_offsets(20.0), [0.0])
        self.assertEqual(DETECTOR.build_probe_offsets(100.0), [3.5, 35.0, 63.0])

    def test_aggregate_samples_uses_majority_and_average_confidence(self):
        samples = [
            {"language": "es", "probability": 0.80},
            {"language": "en", "probability": 0.95},
            {"language": "es", "probability": 0.60},
        ]
        language, confidence = DETECTOR.aggregate_samples(samples)
        self.assertEqual(language, "es")
        self.assertAlmostEqual(confidence, 0.70)


if __name__ == "__main__":
    unittest.main()
