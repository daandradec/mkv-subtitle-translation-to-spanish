#!/usr/bin/env python3
"""Create durable prepare/resume checkpoints for subtitle translation runs."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 2
VALID_STATUSES = (
    "awaiting_translation_maps",
    "translation_maps_resolved",
    "completed",
)


def _powershell_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def _powershell_array(values):
    return "@(" + ",".join(_powershell_quote(value) for value in values) + ")"


def build_resume_command(
    launcher,
    input_mkv,
    stream_index,
    mkv_track_id,
    *,
    source_language_override="",
    source_ass="",
    spanish_ass="",
    tv_safe_srt="",
    normalization_report="",
    skip_spanish_normalization=False,
    embedded_subtitle_format="both",
    output_mkv="",
    term_map_json=(),
):
    command = [
        "&",
        _powershell_quote(Path(launcher).resolve()),
        "-InputMkv",
        _powershell_quote(Path(input_mkv).resolve()),
        "-Resume",
        "-SourceSubtitleStreamIndex",
        str(stream_index),
        "-SourceMkvTrackId",
        str(mkv_track_id),
    ]
    optional_values = (
        ("-SourceLanguageOverride", source_language_override, False),
        ("-EnglishAss", source_ass, True),
        ("-SpanishAss", spanish_ass, True),
        ("-TvSafeSrt", tv_safe_srt, True),
        ("-NormalizationReport", normalization_report, True),
        ("-EmbeddedSubtitleFormat", embedded_subtitle_format, False),
        ("-OutputMkv", output_mkv, True),
    )
    for parameter, value, resolve_path in optional_values:
        if value:
            effective_value = Path(value).resolve() if resolve_path else value
            command.extend((parameter, _powershell_quote(effective_value)))
    if skip_spanish_normalization:
        command.append("-SkipSpanishNormalization")
    if term_map_json:
        resolved_terms = tuple(Path(path).resolve() for path in term_map_json)
        command.extend(("-TermMapJson", _powershell_array(resolved_terms)))
    return " ".join(command)


def build_checkpoint(
    *,
    status,
    output_name,
    input_mkv,
    source_ass,
    source_language,
    source_language_name,
    source_codec,
    stream_index,
    mkv_track_id,
    translations_dir,
    launcher,
    source_language_override="",
    spanish_ass="",
    tv_safe_srt="",
    normalization_report="",
    skip_spanish_normalization=False,
    embedded_subtitle_format="both",
    output_mkv="",
    term_map_json=(),
    created_at_utc=None,
):
    if status not in VALID_STATUSES:
        raise ValueError(f"Unsupported workflow checkpoint status: {status}")

    input_path = Path(input_mkv).resolve()
    source_ass_path = Path(source_ass).resolve()
    translations_path = Path(translations_dir).resolve()
    language_dir = translations_path / source_language
    now = datetime.now(timezone.utc).isoformat()
    resume_arguments = {
        "InputMkv": str(input_path),
        "Resume": True,
        "SourceSubtitleStreamIndex": stream_index,
        "SourceMkvTrackId": mkv_track_id,
        "SourceLanguageOverride": source_language_override,
        "EnglishAss": str(source_ass_path),
        "SpanishAss": str(Path(spanish_ass).resolve()) if spanish_ass else "",
        "TvSafeSrt": str(Path(tv_safe_srt).resolve()) if tv_safe_srt else "",
        "NormalizationReport": (
            str(Path(normalization_report).resolve()) if normalization_report else ""
        ),
        "SkipSpanishNormalization": bool(skip_spanish_normalization),
        "EmbeddedSubtitleFormat": embedded_subtitle_format,
        "OutputMkv": str(Path(output_mkv).resolve()) if output_mkv else "",
        "TermMapJson": [str(Path(path).resolve()) for path in term_map_json],
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "created_at_utc": created_at_utc or now,
        "updated_at_utc": now,
        "output_name": output_name,
        "input_mkv": str(input_path),
        "source_subtitle": {
            "path": str(source_ass_path),
            "language": source_language,
            "language_name": source_language_name,
            "codec": source_codec,
            "ffprobe_stream_index": stream_index,
            "mkvmerge_track_id": mkv_track_id,
        },
        "translation_maps": {
            "directory": str(language_dir),
            "preferred_file": str(language_dir / "translations_all.json"),
            "fallback_pattern": str(language_dir / "translations_*.json"),
        },
        "resume": {
            "launcher": str(Path(launcher).resolve()),
            "arguments": resume_arguments,
            "command": build_resume_command(
                launcher,
                input_path,
                stream_index,
                mkv_track_id,
                source_language_override=source_language_override,
                source_ass=source_ass_path,
                spanish_ass=spanish_ass,
                tv_safe_srt=tv_safe_srt,
                normalization_report=normalization_report,
                skip_spanish_normalization=skip_spanish_normalization,
                embedded_subtitle_format=embedded_subtitle_format,
                output_mkv=output_mkv,
                term_map_json=term_map_json,
            ),
        },
    }


def write_checkpoint(checkpoint_path, **values):
    checkpoint = Path(checkpoint_path)
    created_at_utc = None
    if checkpoint.is_file():
        try:
            existing = json.loads(checkpoint.read_text(encoding="utf-8-sig"))
            if (
                existing.get("output_name") == values["output_name"]
                and existing.get("input_mkv") == str(Path(values["input_mkv"]).resolve())
            ):
                created_at_utc = existing.get("created_at_utc")
        except (OSError, UnicodeError, json.JSONDecodeError):
            created_at_utc = None

    payload = build_checkpoint(created_at_utc=created_at_utc, **values)
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8-sig",
    )
    return payload


def main():
    parser = argparse.ArgumentParser(
        description="Write a durable checkpoint for the subtitle translation workflow."
    )
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--status", required=True, choices=VALID_STATUSES)
    parser.add_argument("--output-name", required=True)
    parser.add_argument("--input-mkv", required=True)
    parser.add_argument("--source-ass", required=True)
    parser.add_argument("--source-language", required=True)
    parser.add_argument("--source-language-name", required=True)
    parser.add_argument("--source-codec", required=True)
    parser.add_argument("--stream-index", required=True, type=int)
    parser.add_argument("--mkv-track-id", required=True, type=int)
    parser.add_argument("--translations-dir", required=True)
    parser.add_argument("--launcher", required=True)
    parser.add_argument("--source-language-override", default="")
    parser.add_argument("--spanish-ass", default="")
    parser.add_argument("--tv-safe-srt", default="")
    parser.add_argument("--normalization-report", default="")
    parser.add_argument("--skip-spanish-normalization", action="store_true")
    parser.add_argument("--embedded-subtitle-format", default="both")
    parser.add_argument("--output-mkv", default="")
    parser.add_argument("--term-map-json", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload = write_checkpoint(
        args.checkpoint,
        status=args.status,
        output_name=args.output_name,
        input_mkv=args.input_mkv,
        source_ass=args.source_ass,
        source_language=args.source_language,
        source_language_name=args.source_language_name,
        source_codec=args.source_codec,
        stream_index=args.stream_index,
        mkv_track_id=args.mkv_track_id,
        translations_dir=args.translations_dir,
        launcher=args.launcher,
        source_language_override=args.source_language_override,
        spanish_ass=args.spanish_ass,
        tv_safe_srt=args.tv_safe_srt,
        normalization_report=args.normalization_report,
        skip_spanish_normalization=args.skip_spanish_normalization,
        embedded_subtitle_format=args.embedded_subtitle_format,
        output_mkv=args.output_mkv,
        term_map_json=args.term_map_json,
    )
    if args.json:
        # Windows PowerShell may expose a legacy console encoding even though the
        # checkpoint file itself is UTF-8. Escaping non-ASCII here keeps the JSON
        # transport parseable without altering the persisted text.
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    else:
        print(args.checkpoint)


if __name__ == "__main__":
    main()
