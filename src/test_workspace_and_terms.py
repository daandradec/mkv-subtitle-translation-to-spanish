import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from subtitle_workspace import build_workspace, make_workspace_id, semantic_prefix
from translation_maps import find_translation_maps
from translation_terms import apply_terms, load_term_maps


class WorkspaceAndTermsTests(unittest.TestCase):
    def test_semantic_prefix_uses_words_without_exceeding_limit(self):
        prefix = semantic_prefix("Love Live Nijigasaki High School Idol Club", max_length=24)
        self.assertEqual(prefix, "Love-Live-Nijigasaki")
        self.assertLessEqual(len(prefix), 24)

    def test_workspace_id_uses_prefix_separator_and_six_char_suffix(self):
        workspace_id = make_workspace_id("input/NIPPON SANGOKU.mkv", suffix="a1b2c3")
        self.assertEqual(workspace_id, "NIPPON-SANGOKU-A1B2C3")
        self.assertLessEqual(len(workspace_id), 31)

    def test_workspace_paths_share_same_id(self):
        workspace = build_workspace("input/NIPPON SANGOKU.mkv", "NIPPON-SANGOKU-A1B2C3")
        subtitle_dir = workspace["subtitle_work_dir"].replace("\\", "/")
        translations_dir = workspace["translations_dir"].replace("\\", "/")
        output_dir = workspace["output_dir"].replace("\\", "/")
        self.assertIn("subtitle_work/NIPPON-SANGOKU-A1B2C3", subtitle_dir)
        self.assertIn("translations/NIPPON-SANGOKU-A1B2C3", translations_dir)
        self.assertIn("output/NIPPON-SANGOKU-A1B2C3", output_dir)
        self.assertIn("output/NIPPON-SANGOKU-A1B2C3/NIPPON SANGOKU.spa.ass", workspace["spanish_ass"].replace("\\", "/"))
        self.assertIn("output/NIPPON-SANGOKU-A1B2C3/NIPPON SANGOKU.spa.srt", workspace["tv_safe_srt"].replace("\\", "/"))
        self.assertIn("output/NIPPON-SANGOKU-A1B2C3/NIPPON SANGOKU.spa.mkv", workspace["output_mkv"].replace("\\", "/"))

    def test_default_term_map_normalizes_japanese_names(self):
        terms = load_term_maps([])
        text = "長尾武兎惇 ordenó avanzar hacia 金沢 y 大和."
        self.assertEqual(apply_terms(text, terms), "Nagao Buton ordenó avanzar hacia Kanazawa y Yamato.")

    def test_default_term_map_also_handles_mojibake_names(self):
        terms = load_term_maps([])
        text = "長尾武兎惇 ordenó avanzar hacia 金沢 y 大和."
        mojibake = text.encode("utf-8").decode("cp1252", errors="ignore")
        self.assertEqual(apply_terms(mojibake, terms), "Nagao Buton ordenÃ³ avanzar hacia Kanazawa y Yamato.")

    def test_translation_maps_resolve_per_workspace_language(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            language_dir = base / "en"
            language_dir.mkdir()
            first = language_dir / "translations_dialogue_part1.json"
            second = language_dir / "translations_songs.json"
            first.write_text('{"1":"Uno"}', encoding="utf-8")
            second.write_text('{"2":"Dos"}', encoding="utf-8")
            self.assertEqual(find_translation_maps(base, "en"), [first, second])

    def test_translation_maps_prefer_combined_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            language_dir = base / "ja"
            language_dir.mkdir()
            all_maps = language_dir / "translations_all.json"
            chunk = language_dir / "translations_chunk_01.json"
            all_maps.write_text('{"1":"Uno"}', encoding="utf-8")
            chunk.write_text('{"2":"Dos"}', encoding="utf-8")
            self.assertEqual(find_translation_maps(base, "ja"), [all_maps])


if __name__ == "__main__":
    unittest.main()
