#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from languages import UnsupportedLanguageError, get_language_profile
from subtitle_text_to_ass import convert_text_subtitle_to_ass, parse_text_subtitles


LANGUAGE_TO_MKV = {
    "en": ("eng", "Ingles"),
    "english": ("eng", "Ingles"),
    "es": ("spa", "Espanol"),
    "spanish": ("spa", "Espanol"),
    "ja": ("jpn", "Japones"),
    "japanese": ("jpn", "Japones"),
    "zh": ("chi", "Chino"),
    "chinese": ("chi", "Chino"),
    "cmn": ("chi", "Chino mandarin"),
    "hi": ("hin", "Hindi"),
    "hindi": ("hin", "Hindi"),
    "pt": ("por", "Portugues"),
    "portuguese": ("por", "Portugues"),
    "fr": ("fre", "Frances"),
    "french": ("fre", "Frances"),
    "ru": ("rus", "Ruso"),
    "russian": ("rus", "Ruso"),
    "de": ("ger", "Aleman"),
    "german": ("ger", "Aleman"),
    "ko": ("kor", "Coreano"),
    "korean": ("kor", "Coreano"),
    "it": ("ita", "Italiano"),
    "italian": ("ita", "Italiano"),
    "wuu": ("wuu", "Chino Wu"),
}


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


def postprocess_transcription(raw_output_dir, audio_stem, output_srt, output_ass, report_path, backend, requested_language=""):
    input_srt = find_backend_output(raw_output_dir, audio_stem, ".srt")
    raw_json = find_backend_output(raw_output_dir, audio_stem, ".json")
    if not input_srt:
        raise RuntimeError(f"No se encontro SRT generado por el backend en {raw_output_dir}.")

    cues = parse_text_subtitles(input_srt, "srt")
    if not cues:
        raise RuntimeError("La transcripcion no produjo cues validos; no se generara MKV final.")

    write_clean_srt(cues, output_srt)
    ass_result = convert_text_subtitle_to_ass(
        Path(output_srt),
        Path(output_ass),
        title="Transcripcion generada desde audio",
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
