import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from normalize_spanish_subtitles import normalize_files, normalize_spanish_text, parse_srt


ASS_HEADER = """[Script Info]
Title: test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,40,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,30,1
Style: SongEnglish,Arial,40,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,30,1
Style: Romaji,Arial,40,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,8,10,10,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


class SpanishNormalizationTests(unittest.TestCase):
    def test_normalize_common_spanish_accents(self):
        text = "Se que tu y yo estaremos aqui mas dias con el corazon y la pasi?n"
        self.assertEqual(
            normalize_spanish_text(text),
            "Sé que tú y yo estaremos aquí más días con el corazón y la pasión",
        )

    def test_normalize_mojibake_question_and_song_accents(self):
        text = (
            "Ese evento termin?, ?verdad?\n"
            "Quiza seria dificil. Los suenos seran manana?\n"
            "Quiza todo seria más simple??\n"
            "No te haria todo más dificil?\n"
            "¡¡Aún falta más! ¿¿No termino?\n"
            "Estan ahí, lo se"
        )
        self.assertEqual(
            normalize_spanish_text(text),
            "Ese evento terminó, ¿verdad?\n"
            "Quizá sería difícil. Los sueños serán mañana?\n"
            "¿Quizá todo sería más simple?\n"
            "¿No te haría todo más difícil?\n"
            "¡Aún falta más! ¿No termino?\n"
            "Están ahí, lo sé",
        )

    def test_normalize_files_preserves_overlapping_cues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ass = root / "input.ass"
            srt = root / "input.srt"
            out_ass = root / "out.ass"
            out_srt = root / "out.srt"
            report = root / "report.json"
            ass.write_text(
                ASS_HEADER
                + "Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,Se que tu y yo\n"
                + "Dialogue: 1,0:00:01.00,0:00:03.00,SongEnglish,,0,0,0,,Mi corazon canta\n"
                + "Dialogue: 2,0:00:01.00,0:00:03.00,Romaji,,0,0,0,,kokoro\n"
                + "Dialogue: 0,0:00:04.00,0:00:05.00,Default,,0,0,0,,ffffffffffff\n",
                encoding="utf-8",
            )
            srt.write_text(
                "1\n00:00:01,000 --> 00:00:03,000\nSe que tu y yo\n\n",
                encoding="utf-8",
            )

            normalize_files(ass, srt, out_ass, out_srt, report)
            cues = parse_srt(out_srt)

            self.assertEqual(len(cues), 2)
            self.assertEqual(cues[0]["text"], "Mi corazón canta")
            self.assertEqual(cues[1]["text"], "Sé que tú y yo")
            self.assertNotIn("ffffffff", out_srt.read_text(encoding="utf-8-sig"))
            self.assertIn("Sé que tú y yo", out_ass.read_text(encoding="utf-8"))
            self.assertIn("Mi corazón canta", out_ass.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
