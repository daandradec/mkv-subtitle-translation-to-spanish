import unittest

from mkv_subtitle_agentic_translation.subtitle_language import (
    TEXT_SUBTITLE_CODECS,
    choose_best_subtitle_candidate,
    find_subtitle_stream,
)


class LanguageProfileTests(unittest.TestCase):
    def test_textual_subtitle_codecs_are_allowed(self):
        self.assertIn("ass", TEXT_SUBTITLE_CODECS)
        self.assertIn("subrip", TEXT_SUBTITLE_CODECS)
        self.assertIn("webvtt", TEXT_SUBTITLE_CODECS)
        self.assertNotIn("hdmv_pgs_subtitle", TEXT_SUBTITLE_CODECS)

    def test_missing_embedded_subtitles_has_clear_message(self):
        with self.assertRaises(ValueError) as ctx:
            find_subtitle_stream({"streams": []}, 3)
        self.assertIn(
            "No se encontraron subtítulos incrustados en el archivo original para traducir a español",
            str(ctx.exception),
        )

    def test_default_subtitle_track_wins_without_explicit_stream(self):
        inventory = {
            "candidates": [
                {
                    "stream_index": 5,
                    "mkv_track_id": 5,
                    "source_language": "fr",
                    "supported": True,
                    "textual": True,
                    "forced_like": False,
                    "cc_like": False,
                    "default": False,
                    "score": (0, 0, 10000, 1000, 500, 500, 0),
                },
                {
                    "stream_index": 8,
                    "mkv_track_id": 8,
                    "source_language": "fr",
                    "supported": True,
                    "textual": True,
                    "forced_like": False,
                    "cc_like": False,
                    "default": True,
                    "score": (0, 0, 10000, 1000, 300, 500, 100),
                },
            ]
        }
        selected, _ = choose_best_subtitle_candidate(inventory)
        self.assertEqual(selected["stream_index"], 8)


if __name__ == "__main__":
    unittest.main()
