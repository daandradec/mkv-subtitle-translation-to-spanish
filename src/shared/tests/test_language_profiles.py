import unittest

from video_toolkit.languages import UnsupportedLanguageError, get_language_profile, normalize_language_code


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


if __name__ == "__main__":
    unittest.main()
