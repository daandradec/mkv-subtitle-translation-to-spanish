"""Discover and run tests from shared code and all four skill projects."""

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
TEST_DIRS = [
    SRC_DIR / "shared" / "tests",
    SRC_DIR / "mkv-subtitle-agentic-translation" / "tests",
    SRC_DIR / "video-subtitle-agentic-transcription" / "tests",
    SRC_DIR / "video-text-agent-transcription" / "tests",
    SRC_DIR / "video-voice-cleaner" / "tests",
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
