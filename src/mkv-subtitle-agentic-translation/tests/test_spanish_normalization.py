import tempfile
import unittest
from pathlib import Path

from mkv_subtitle_agentic_translation.normalize_spanish_subtitles import (
    find_suspicious_question_marks,
    normalize_files,
    normalize_spanish_text,
    parse_srt,
)


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

    def test_normalize_translation_mojibake_from_maps(self):
        text = "?Es... escrita de su mano! Demasi?ado sublime... Demasíado. Ry?mon regres? a Fukui. ocasíón"
        normalized = normalize_spanish_text(text)

        self.assertEqual(
            normalized,
            "¡Es... escrita de su mano! Demasiado sublime... Demasiado. Ryumon regresó a Fukui. ocasión",
        )
        self.assertEqual(find_suspicious_question_marks(normalized), [])

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

    def test_normalize_files_trims_adjacent_repeated_suffix_from_previous_cue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ass = root / "input.ass"
            srt = root / "input.srt"
            out_ass = root / "out.ass"
            out_srt = root / "out.srt"
            report = root / "report.json"
            ass.write_text(
                ASS_HEADER
                + "Dialogue: 0,0:05:11.52,0:05:16.90,Default,,0,0,0,,Concentrar todas las fuerzas de forma rápida y segura: no lograrlo equivale a renunciar a la superioridad relativa\n"
                + "Dialogue: 0,0:05:16.94,0:05:20.24,Default,,0,0,0,,no lograrlo equivale a renunciar a la superioridad relativa\n",
                encoding="utf-8",
            )
            srt.write_text("", encoding="utf-8")

            normalize_files(ass, srt, out_ass, out_srt, report)
            cues = parse_srt(out_srt)

            self.assertEqual(cues[0]["text"], "Concentrar todas las fuerzas de forma rápida y segura.")
            self.assertEqual(cues[1]["text"], "no lograrlo equivale a renunciar a la superioridad relativa")

    def test_normalize_files_trims_short_sentence_repeated_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ass = root / "input.ass"
            srt = root / "input.srt"
            out_ass = root / "out.ass"
            out_srt = root / "out.srt"
            report = root / "report.json"
            ass.write_text(
                ASS_HEADER
                + "Dialogue: 0,0:19:46.35,0:19:49.19,Default,,0,0,0,,comandante supremo Wajima. Creo que metí la pata.\n"
                + "Dialogue: 0,0:19:49.21,0:19:54.85,Default,,0,0,0,,Creo que metí la pata.\n",
                encoding="utf-8",
            )
            srt.write_text("", encoding="utf-8")

            normalize_files(ass, srt, out_ass, out_srt, report)
            cues = parse_srt(out_srt)

            self.assertEqual(cues[0]["text"], "comandante supremo Wajima.")
            self.assertEqual(cues[1]["text"], "Creo que metí la pata.")

    def test_normalize_files_removes_short_bridge_duplicate_cue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ass = root / "input.ass"
            srt = root / "input.srt"
            out_ass = root / "out.ass"
            out_srt = root / "out.srt"
            report = root / "report.json"
            ass.write_text(
                ASS_HEADER
                + "Dialogue: 0,0:05:01.39,0:05:05.92,Default,,0,0,0,,Intentar defender cada base por separado, con una táctica de línea de centinelas,\n"
                + "Dialogue: 0,0:05:05.96,0:05:06.70,Default,,0,0,0,,con una táctica de línea de centinelas, es una mala estrategia que ni siquiera protege el territorio.\n"
                + "Dialogue: 0,0:05:06.74,0:05:09.28,Default,,0,0,0,,es una mala estrategia que ni siquiera protege el territorio. Ya lo entendiste, ¿no?\n",
                encoding="utf-8",
            )
            srt.write_text("", encoding="utf-8")

            normalize_files(ass, srt, out_ass, out_srt, report)
            cues = parse_srt(out_srt)

            self.assertEqual(len(cues), 2)
            self.assertEqual(cues[0]["end_ms"], 306700)
            self.assertEqual(
                cues[0]["text"],
                "Intentar defender cada base por separado, con una táctica de línea de centinelas,",
            )
            self.assertEqual(
                cues[1]["text"],
                "es una mala estrategia que ni siquiera protege el territorio. Ya lo entendiste, ¿no?",
            )

    def test_normalize_files_removes_bridge_duplicate_up_to_1800_ms(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ass = root / "input.ass"
            srt = root / "input.srt"
            out_ass = root / "out.ass"
            out_srt = root / "out.srt"
            report = root / "report.json"
            ass.write_text(
                ASS_HEADER
                + "Dialogue: 0,0:01:10.82,0:01:13.22,Default,,0,0,0,,Demasiado sublime... Nagao Buton?\n"
                + "Dialogue: 0,0:01:13.24,0:01:14.83,Default,,0,0,0,,Nagao Buton? Ahora sí me siento motivado.\n"
                + "Dialogue: 0,0:01:14.91,0:01:17.65,Default,,0,0,0,,Ahora sí me siento motivado.\n",
                encoding="utf-8",
            )
            srt.write_text("", encoding="utf-8")

            normalize_files(ass, srt, out_ass, out_srt, report)
            cues = parse_srt(out_srt)

            self.assertEqual(len(cues), 2)
            self.assertEqual(cues[0]["end_ms"], 74830)
            self.assertEqual(cues[0]["text"], "Demasiado sublime... Nagao Buton?")
            self.assertEqual(cues[1]["text"], "Ahora sí me siento motivado.")

    def test_normalize_files_removes_short_exact_duplicate_cue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ass = root / "input.ass"
            srt = root / "input.srt"
            out_ass = root / "out.ass"
            out_srt = root / "out.srt"
            report = root / "report.json"
            ass.write_text(
                ASS_HEADER
                + "Dialogue: 0,0:05:06.74,0:05:09.28,Default,,0,0,0,,es una mala estrategia que ni siquiera protege el territorio. Ya lo entendiste, ¿no?\n"
                + "Dialogue: 0,0:05:09.32,0:05:10.38,Default,,0,0,0,,es una mala estrategia que ni siquiera protege el territorio. Ya lo entendiste, ¿no?\n"
                + "Dialogue: 0,0:05:11.52,0:05:16.90,Default,,0,0,0,,Concentrar todas las fuerzas de forma rápida y segura.\n",
                encoding="utf-8",
            )
            srt.write_text("", encoding="utf-8")

            normalize_files(ass, srt, out_ass, out_srt, report)
            cues = parse_srt(out_srt)

            self.assertEqual(len(cues), 2)
            self.assertEqual(cues[0]["end_ms"], 310380)
            self.assertEqual(
                cues[0]["text"],
                "es una mala estrategia que ni siquiera protege el territorio. Ya lo entendiste, ¿no?",
            )
            self.assertEqual(cues[1]["text"], "Concentrar todas las fuerzas de forma rápida y segura.")

    def test_normalize_files_merges_exact_adjacent_duplicate_even_when_short_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ass = root / "input.ass"
            srt = root / "input.srt"
            out_ass = root / "out.ass"
            out_srt = root / "out.srt"
            report = root / "report.json"
            ass.write_text(
                ASS_HEADER
                + "Dialogue: 0,0:00:45.30,0:00:46.58,Default,,0,0,0,,Sí. Todo esto fue posible\n"
                + "Dialogue: 0,0:00:46.60,0:00:48.10,Default,,0,0,0,,Sí. Todo esto fue posible\n"
                + "Dialogue: 0,0:00:48.20,0:00:50.00,Default,,0,0,0,,gracias al plan.\n",
                encoding="utf-8",
            )
            srt.write_text("", encoding="utf-8")

            normalize_files(ass, srt, out_ass, out_srt, report)
            cues = parse_srt(out_srt)

            self.assertEqual(len(cues), 2)
            self.assertEqual(cues[0]["end_ms"], 48100)
            self.assertEqual(cues[0]["text"], "Sí. Todo esto fue posible")

    def test_normalize_files_redistributes_repeated_prefix_with_new_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ass = root / "input.ass"
            srt = root / "input.srt"
            out_ass = root / "out.ass"
            out_srt = root / "out.srt"
            report = root / "report.json"
            ass.write_text(
                ASS_HEADER
                + "Dialogue: 0,0:01:08.94,0:01:10.72,Default,,0,0,0,,¡Es... escrita de su mano! Demasiado sublime...\n"
                + "Dialogue: 0,0:01:10.82,0:01:13.22,Default,,0,0,0,,¡Es... escrita de su mano! Demasiado sublime... Nagao Buton?\n",
                encoding="utf-8",
            )
            srt.write_text("", encoding="utf-8")

            normalize_files(ass, srt, out_ass, out_srt, report)
            cues = parse_srt(out_srt)

            self.assertEqual(len(cues), 2)
            self.assertEqual(cues[0]["text"], "¡Es... escrita de su mano!")
            self.assertEqual(cues[1]["text"], "Demasiado sublime... Nagao Buton?")


if __name__ == "__main__":
    unittest.main()
