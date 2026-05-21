import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from languages import UnsupportedLanguageError, get_language_profile, normalize_language_code
from subtitle_language import TEXT_SUBTITLE_CODECS, choose_best_subtitle_candidate, find_subtitle_stream


class LanguageProfileTests(unittest.TestCase):
    def test_supported_aliases_normalize(self):
        cases = {
            "eng": "en",
            "English": "en",
            "en-US": "en",
            "jpn": "ja",
            "Japanese": "ja",
            "ja-JP": "ja",
            "日本語": "ja",
            "chi": "zh-cmn",
            "zho": "zh-cmn",
            "cmn": "zh-cmn",
            "zh": "zh-cmn",
            "zh-Hans": "zh-cmn",
            "普通话": "zh-cmn",
            "wuu": "wuu",
            "Shanghainese": "wuu",
            "上海话": "wuu",
            "kor": "ko",
            "한국어": "ko",
            "deu": "de",
            "ger": "de",
            "fra": "fr",
            "fre": "fr",
            "fr-FR": "fr",
            "français": "fr",
            "por": "pt",
            "pt-BR": "pt",
            "hin": "hi",
            "हिन्दी": "hi",
            "rus": "ru",
            "русский": "ru",
            "ita": "it",
        }
        for alias, expected in cases.items():
            with self.subTest(alias=alias):
                self.assertEqual(normalize_language_code(alias), expected)

    def test_profile_lookup(self):
        self.assertEqual(get_language_profile("japonés").code, "ja")

    def test_unsupported_language_fails_with_allowed_list(self):
        with self.assertRaises(UnsupportedLanguageError) as ctx:
            normalize_language_code("latin")
        self.assertIn("Idiomas disponibles", str(ctx.exception))

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
