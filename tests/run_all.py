"""Discover and run tests from shared code and all three skill projects."""

import os
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
TEMPORARY_ROOT = PROJECT_ROOT / ".tmp"
TEST_TEMPORARY_ROOT = TEMPORARY_ROOT / "tests"
CACHE_ROOT = PROJECT_ROOT / ".cache"
TEST_TEMPORARY_ROOT.mkdir(parents=True, exist_ok=True)
CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("VIDEO_TOOLKIT_TMP_ROOT", str(TEMPORARY_ROOT))
os.environ.setdefault("VIDEO_TOOLKIT_CACHE_ROOT", str(CACHE_ROOT))
os.environ.setdefault("VIDEO_TOOLKIT_TEMP_CATEGORY", "tests")
os.environ.setdefault("TEMP", str(TEST_TEMPORARY_ROOT))
os.environ.setdefault("TMP", str(TEST_TEMPORARY_ROOT))
os.environ.setdefault("TMPDIR", str(TEST_TEMPORARY_ROOT))
os.environ.setdefault("PIP_CACHE_DIR", str(CACHE_ROOT / "pip"))
os.environ.setdefault("PYTHONPYCACHEPREFIX", str(CACHE_ROOT / "python"))
os.environ.setdefault("HF_HOME", str(CACHE_ROOT / "models" / "huggingface"))
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(CACHE_ROOT / "models" / "huggingface" / "hub"))
os.environ.setdefault("TORCH_HOME", str(CACHE_ROOT / "models" / "torch"))
os.environ.setdefault("WHISPER_CACHE_DIR", str(CACHE_ROOT / "models" / "whisper"))
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_ROOT / "runtime"))
tempfile.tempdir = str(TEST_TEMPORARY_ROOT)

PYTHON_ROOTS = [
    SRC_DIR / "shared",
    SRC_DIR / "video-generate-traslated-subtitles-from-existing-subtitles" / "python",
    SRC_DIR / "video-generate-new-subtitles-from-audio" / "python",
    SRC_DIR / "video-generate-whisper-transcription" / "python",
]
TEST_DIRS = [
    PROJECT_ROOT / "tests",
    SRC_DIR / "video-generate-traslated-subtitles-from-existing-subtitles" / "tests",
    SRC_DIR / "video-generate-new-subtitles-from-audio" / "tests",
    SRC_DIR / "video-generate-whisper-transcription" / "tests",
]


def configure_python_paths():
    for root in reversed(PYTHON_ROOTS):
        value = str(root)
        if value not in sys.path:
            sys.path.insert(0, value)


def build_suite(pattern="test_*.py"):
    configure_python_paths()
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for test_dir in TEST_DIRS:
        suite.addTests(
            loader.discover(
                start_dir=str(test_dir),
                pattern=pattern,
                top_level_dir=str(test_dir),
            )
        )
    return suite


def main():
    result = unittest.TextTestRunner(verbosity=1).run(build_suite())
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
