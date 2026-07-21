import importlib
import inspect
import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[2]
PYTHON_ROOTS = [
    SRC_DIR / "shared" / "python",
    SRC_DIR / "video-generate-traslated-subtitles-from-existing-subtitles" / "python",
    SRC_DIR / "video-generate-new-subtitles-from-audio" / "python",
    SRC_DIR / "video-generate-whisper-transcription" / "python",
]
for root in reversed(PYTHON_ROOTS):
    value = str(root)
    if value not in sys.path:
        sys.path.insert(0, value)


class CanonicalEntrypointTests(unittest.TestCase):
    def test_canonical_python_modules_expose_main(self):
        modules = [
            "video_generate_traslated_subtitles_from_existing_subtitles.ass_apply_translations",
            "video_generate_traslated_subtitles_from_existing_subtitles.ass_to_tv_safe_srt",
            "video_generate_traslated_subtitles_from_existing_subtitles.normalize_spanish_subtitles",
            "video_generate_traslated_subtitles_from_existing_subtitles.normalize_translation_maps",
            "video_generate_traslated_subtitles_from_existing_subtitles.subtitle_language",
            "video_generate_traslated_subtitles_from_existing_subtitles.translation_maps",
            "video_generate_traslated_subtitles_from_existing_subtitles.translation_terms",
            "video_generate_traslated_subtitles_from_existing_subtitles.workflow_checkpoint",
            "video_generate_traslated_subtitles_from_existing_subtitles.workspace",
            "video_toolkit.subtitles.text",
            "video_toolkit.transcription.backend",
            "video_generate_new_subtitles_from_audio.postprocess",
            "video_generate_new_subtitles_from_audio.remux",
            "video_generate_new_subtitles_from_audio.workspace",
            "video_generate_whisper_transcription.postprocess",
            "video_generate_whisper_transcription.workspace",
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
            "video-generate-traslated-subtitles-from-existing-subtitles",
            "shared",
            "video-generate-new-subtitles-from-audio",
            "video-generate-whisper-transcription",
        }
        entries = {entry.name for entry in SRC_DIR.iterdir()}
        self.assertEqual(entries, expected)
        self.assertTrue(all((SRC_DIR / name).is_dir() for name in expected))


if __name__ == "__main__":
    unittest.main()
