#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

from languages import UnsupportedLanguageError, get_language_profile
from subtitle_text_to_ass import TextCue, convert_text_subtitle_to_ass, parse_text_subtitles


LANGUAGE_TO_MKV = {
    "en": ("eng", "Ingl\u00e9s"),
    "english": ("eng", "Ingl\u00e9s"),
    "es": ("spa", "Espa\u00f1ol"),
    "spanish": ("spa", "Espa\u00f1ol"),
    "ja": ("jpn", "Japon\u00e9s"),
    "japanese": ("jpn", "Japon\u00e9s"),
    "zh": ("chi", "Chino"),
    "chinese": ("chi", "Chino"),
    "cmn": ("chi", "Chino mandar\u00edn"),
    "hi": ("hin", "Hindi"),
    "hindi": ("hin", "Hindi"),
    "pt": ("por", "Portugu\u00e9s"),
    "portuguese": ("por", "Portugu\u00e9s"),
    "fr": ("fre", "Franc\u00e9s"),
    "french": ("fre", "Franc\u00e9s"),
    "ru": ("rus", "Ruso"),
    "russian": ("rus", "Ruso"),
    "de": ("ger", "Alem\u00e1n"),
    "german": ("ger", "Alem\u00e1n"),
    "ko": ("kor", "Coreano"),
    "korean": ("kor", "Coreano"),
    "it": ("ita", "Italiano"),
    "italian": ("ita", "Italiano"),
    "wuu": ("wuu", "Chino Wu"),
}


WORD_RE = re.compile(r"\S+")


def find_backend_output(raw_output_dir, audio_stem, suffix):
    candidates = [
        Path(raw_output_dir) / f"{audio_stem}{suffix}",
        Path(raw_output_dir) / suffix.lstrip("."),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    matches = sorted(Path(raw_output_dir).glob(f"*{suffix}"))
    return matches[0] if matches else None


def ms_to_srt_time(value):
    hours, remainder = divmod(value, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def normalize_visible_text(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def wrap_words(words, max_line_chars=52, max_lines=2):
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_line_chars or not current:
            current = candidate
            continue
        lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines if len(lines) <= max_lines else None


def write_clean_srt(cues, output_srt):
    output_srt = Path(output_srt)
    output_srt.parent.mkdir(parents=True, exist_ok=True)
    blocks = []
    for index, cue in enumerate(cues, start=1):
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{ms_to_srt_time(cue.start_ms)} --> {ms_to_srt_time(cue.end_ms)}",
                    cue.text,
                ]
            )
        )
    output_srt.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def read_detected_language(raw_json_path, requested_language=""):
    if requested_language:
        return requested_language
    if raw_json_path and Path(raw_json_path).exists():
        try:
            data = json.loads(Path(raw_json_path).read_text(encoding="utf-8-sig"))
            return str(data.get("language") or "").strip()
        except json.JSONDecodeError:
            return ""
    return ""


def language_metadata(language):
    key = (language or "").strip().casefold()
    if key in LANGUAGE_TO_MKV:
        mkv_language, display = LANGUAGE_TO_MKV[key]
    elif key:
        mkv_language, display = key, language
    else:
        mkv_language, display = "und", "desconocido"

    translation_supported = True
    translation_warning = ""
    try:
        get_language_profile(key)
    except UnsupportedLanguageError:
        translation_supported = False
        translation_warning = (
            "El idioma transcrito no esta dentro de los idiomas soportados por "
            "mkv-subtitle-agentic-translation; el MKV transcrito es valido, "
            "pero la traduccion automatica posterior podria detenerse."
        )

    return {
        "detected_language": language or "und",
        "mkv_language": mkv_language,
        "language_display": display,
        "translation_supported": translation_supported,
        "translation_warning": translation_warning,
    }


def split_plain_words(text):
    return [match.group(0) for match in WORD_RE.finditer(normalize_visible_text(text))]


def group_words_for_two_lines(words, max_line_chars=52, max_lines=2):
    groups = []
    current = []
    for word in words:
        candidate = current + [word]
        if wrap_words(candidate, max_line_chars=max_line_chars, max_lines=max_lines) is not None:
            current = candidate
            continue
        if current:
            groups.append(current)
        current = [word]
    if current:
        groups.append(current)
    return groups


def reflow_cues(cues, max_line_chars=52, max_lines=2):
    reflowed = []
    for cue in cues:
        groups = group_words_for_two_lines(split_plain_words(cue.text), max_line_chars=max_line_chars, max_lines=max_lines)
        if not groups:
            continue
        total_weight = sum(max(1, sum(len(word) for word in group)) for group in groups)
        duration = cue.end_ms - cue.start_ms
        cursor = cue.start_ms
        for index, group in enumerate(groups, start=1):
            if index == len(groups):
                end_ms = cue.end_ms
            else:
                weight = max(1, sum(len(word) for word in group))
                end_ms = cursor + max(250, round(duration * weight / total_weight))
                end_ms = min(end_ms, cue.end_ms)
            lines = wrap_words(group, max_line_chars=max_line_chars, max_lines=max_lines) or [" ".join(group)]
            if end_ms > cursor:
                reflowed.append(TextCue(start_ms=cursor, end_ms=end_ms, text="\n".join(lines)))
            cursor = end_ms
    return reflowed


def timed_word_groups(raw_json_path, max_line_chars=52, max_lines=2):
    if not raw_json_path or not Path(raw_json_path).exists():
        return []
    try:
        data = json.loads(Path(raw_json_path).read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []

    groups = []
    for segment in data.get("segments", []):
        timed_words = []
        for word in segment.get("words", []):
            value = normalize_visible_text(word.get("word", ""))
            if not value or "start" not in word or "end" not in word:
                continue
            timed_words.append({"word": value, "start": float(word["start"]), "end": float(word["end"])})
        current = []
        for word in timed_words:
            candidate = current + [word]
            candidate_words = [item["word"] for item in candidate]
            if wrap_words(candidate_words, max_line_chars=max_line_chars, max_lines=max_lines) is not None:
                current = candidate
                continue
            if current:
                groups.append(current)
            current = [word]
        if current:
            groups.append(current)
    return groups


def cues_from_timed_word_groups(groups, max_line_chars=52, max_lines=2):
    cues = []
    for group in groups:
        words = [item["word"] for item in group]
        lines = wrap_words(words, max_line_chars=max_line_chars, max_lines=max_lines) or [" ".join(words)]
        start_ms = max(0, int(round(group[0]["start"] * 1000)))
        end_ms = max(0, int(round(group[-1]["end"] * 1000)))
        if end_ms > start_ms:
            cues.append(TextCue(start_ms=start_ms, end_ms=end_ms, text="\n".join(lines)))
    return cues


def readable_cues(input_srt, raw_json, max_line_chars=52, max_lines=2):
    timed_groups = timed_word_groups(raw_json, max_line_chars=max_line_chars, max_lines=max_lines)
    timed_cues = cues_from_timed_word_groups(timed_groups, max_line_chars=max_line_chars, max_lines=max_lines)
    if timed_cues:
        return timed_cues
    return reflow_cues(parse_text_subtitles(input_srt, "srt"), max_line_chars=max_line_chars, max_lines=max_lines)


def postprocess_transcription(
    raw_output_dir,
    audio_stem,
    output_srt,
    output_ass,
    report_path,
    backend,
    requested_language="",
    max_line_chars=52,
    max_lines=2,
):
    input_srt = find_backend_output(raw_output_dir, audio_stem, ".srt")
    raw_json = find_backend_output(raw_output_dir, audio_stem, ".json")
    if not input_srt:
        raise RuntimeError(f"No se encontro SRT generado por el backend en {raw_output_dir}.")

    cues = readable_cues(input_srt, raw_json, max_line_chars=max_line_chars, max_lines=max_lines)
    if not cues:
        raise RuntimeError("La transcripcion no produjo cues validos; no se generara MKV final.")

    write_clean_srt(cues, output_srt)
    ass_result = convert_text_subtitle_to_ass(
        Path(output_srt),
        Path(output_ass),
        title="Transcripcion generada desde audio",
        margin_l=192,
        margin_r=192,
    )

    detected_language = read_detected_language(raw_json, requested_language)
    metadata = language_metadata(detected_language)
    report = {
        "backend": backend,
        "input_srt": str(input_srt),
        "raw_json": str(raw_json) if raw_json else "",
        "output_srt": str(output_srt),
        "output_ass": str(output_ass),
        "cue_count": len(cues),
        "ass_dialogues": ass_result["written_dialogues"],
        "max_lines": max_lines,
        "max_line_chars": max_line_chars,
        "ass_margin_l": 192,
        "ass_margin_r": 192,
        **metadata,
    }
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="Postprocess Whisper/WhisperX subtitle outputs.")
    parser.add_argument("--raw-output-dir", required=True)
    parser.add_argument("--audio-stem", required=True)
    parser.add_argument("--output-srt", required=True)
    parser.add_argument("--output-ass", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--requested-language", default="")
    parser.add_argument("--max-line-chars", type=int, default=52)
    parser.add_argument("--max-lines", type=int, default=2)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        report = postprocess_transcription(
            raw_output_dir=Path(args.raw_output_dir),
            audio_stem=args.audio_stem,
            output_srt=Path(args.output_srt),
            output_ass=Path(args.output_ass),
            report_path=Path(args.report),
            backend=args.backend,
            requested_language=args.requested_language,
            max_line_chars=args.max_line_chars,
            max_lines=args.max_lines,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc))

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"written cues: {report['cue_count']}")
        print(f"written: {report['output_srt']}")
        print(f"written: {report['output_ass']}")
        if report["translation_warning"]:
            print(report["translation_warning"])


if __name__ == "__main__":
    main()
