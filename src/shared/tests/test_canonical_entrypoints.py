import importlib
import inspect
import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[2]
PYTHON_ROOTS = [
    SRC_DIR / "shared" / "python",
    SRC_DIR / "mkv-subtitle-agentic-translation" / "python",
    SRC_DIR / "video-subtitle-agentic-transcription" / "python",
    SRC_DIR / "video-text-agent-transcription" / "python",
    SRC_DIR / "video-voice-cleaner" / "python",
]
for root in reversed(PYTHON_ROOTS):
    value = str(root)
    if value not in sys.path:
        sys.path.insert(0, value)


class CanonicalEntrypointTests(unittest.TestCase):
    def test_canonical_python_modules_expose_main(self):
        modules = [
            "mkv_subtitle_agentic_translation.ass_apply_translations",
            "mkv_subtitle_agentic_translation.ass_to_tv_safe_srt",
            "mkv_subtitle_agentic_translation.normalize_spanish_subtitles",
            "mkv_subtitle_agentic_translation.normalize_translation_maps",
            "mkv_subtitle_agentic_translation.subtitle_language",
            "mkv_subtitle_agentic_translation.translation_maps",
            "mkv_subtitle_agentic_translation.translation_terms",
            "mkv_subtitle_agentic_translation.workflow_checkpoint",
            "mkv_subtitle_agentic_translation.workspace",
            "video_toolkit.subtitles.text",
            "video_toolkit.transcription.backend",
            "video_subtitle_agentic_transcription.postprocess",
            "video_subtitle_agentic_transcription.remux",
            "video_subtitle_agentic_transcription.workspace",
            "video_text_agent_transcription.postprocess",
            "video_text_agent_transcription.workspace",
            "video_voice_cleaner.voice_cleaner",
        ]
        for module_name in modules:
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                self.assertTrue(callable(module.main))

    def test_shared_functions_keep_stable_signatures(self):
        workspace_ids = importlib.import_module("video_toolkit.workspace_ids")
        artifacts = importlib.import_module("video_toolkit.transcription.artifacts")

        self.assertEqual(
            list(inspect.signature(workspace_ids.output_folder_name).parameters),
            ["input_video"],
        )
        self.assertTrue(callable(artifacts.find_backend_output))
        self.assertTrue(callable(artifacts.read_detected_language))

    def test_src_root_contains_only_canonical_projects(self):
        expected = {
            "mkv-subtitle-agentic-translation",
            "shared",
            "video-subtitle-agentic-transcription",
            "video-text-agent-transcription",
            "video-voice-cleaner",
        }
        entries = {entry.name for entry in SRC_DIR.iterdir()}
        self.assertEqual(entries, expected)
        self.assertTrue(all((SRC_DIR / name).is_dir() for name in expected))


if __name__ == "__main__":
    unittest.main()
