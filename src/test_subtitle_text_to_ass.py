import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from subtitle_text_to_ass import convert_text_subtitle_to_ass


class SubtitleTextToAssTests(unittest.TestCase):
    def test_srt_converts_to_simple_ass_dialogues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.srt"
            output = root / "output.ass"
            source.write_text(
                "1\n"
                "00:00:01,250 --> 00:00:03,500\n"
                "Hello <i>there</i>\n"
                "Second line\n\n",
                encoding="utf-8",
            )

            result = convert_text_subtitle_to_ass(source, output)
            ass_text = output.read_text(encoding="utf-8")

            self.assertEqual(result["input_cues"], 1)
            self.assertEqual(result["written_dialogues"], 1)
            self.assertIn("Dialogue: 0,0:00:01.25,0:00:03.50,Default", ass_text)
            self.assertIn(r"Hello there\NSecond line", ass_text)

    def test_vtt_converts_to_simple_ass_dialogues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.vtt"
            output = root / "output.ass"
            source.write_text(
                "WEBVTT\n\n"
                "cue-1\n"
                "00:00:04.000 --> 00:00:06.200 align:start\n"
                "<v Speaker>Ready<br>Go\n\n",
                encoding="utf-8",
            )

            result = convert_text_subtitle_to_ass(source, output)
            ass_text = output.read_text(encoding="utf-8")

            self.assertEqual(result["input_cues"], 1)
            self.assertEqual(result["written_dialogues"], 1)
            self.assertIn("Dialogue: 0,0:00:04.00,0:00:06.20,Default", ass_text)
            self.assertIn(r"Ready\NGo", ass_text)


if __name__ == "__main__":
    unittest.main()
