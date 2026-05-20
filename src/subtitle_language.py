#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

from languages import (
    SUPPORTED_LANGUAGE_NAMES,
    UnsupportedLanguageError,
    get_language_profile,
)

TEXT_SUBTITLE_CODECS = {
    "ass",
    "ssa",
    "subrip",
    "srt",
    "webvtt",
    "vtt",
    "mov_text",
    "text",
}


def run_ffprobe(input_mkv):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "s",
        "-show_entries",
        "stream=index,codec_name:stream_tags=language,title",
        "-of",
        "json",
        str(input_mkv),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def find_subtitle_stream(probe_data, stream_index):
    streams = probe_data.get("streams", [])
    if stream_index is None:
        if not streams:
            raise ValueError("No se encontraron subtítulos incrustados en el archivo original para traducir a español.")
        return streams[0]
    for stream in streams:
        if int(stream.get("index", -1)) == stream_index:
            return stream
    if not streams:
        raise ValueError("No se encontraron subtítulos incrustados en el archivo original para traducir a español.")
    raise ValueError(f"No se encontró la pista de subtítulos con índice {stream_index}.")


def validate_stream_language(input_mkv, stream_index=None, language_override=""):
    probe_data = run_ffprobe(input_mkv)
    stream = find_subtitle_stream(probe_data, stream_index)
    codec_name = stream.get("codec_name", "")
    if codec_name.casefold() not in TEXT_SUBTITLE_CODECS:
        raise ValueError(
            f"Formato de subtítulo no procesable: {codec_name}. "
            "Solo se soportan subtítulos textuales ASS, SRT/SubRip y VTT/WebVTT."
        )
    tags = stream.get("tags", {})
    detected = language_override or tags.get("language", "")
    profile = get_language_profile(detected)
    return {
        "profile": profile,
        "stream": stream,
        "detected_language": detected,
        "codec_name": codec_name,
        "title": tags.get("title", ""),
    }


def main():
    parser = argparse.ArgumentParser(description="Validate subtitle language against the supported source-language list.")
    parser.add_argument("--input-mkv", required=True)
    parser.add_argument("--stream-index", type=int)
    parser.add_argument("--language-override", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = validate_stream_language(
            Path(args.input_mkv),
            stream_index=args.stream_index,
            language_override=args.language_override,
        )
    except (UnsupportedLanguageError, ValueError) as exc:
        raise SystemExit(str(exc))

    profile = result["profile"]
    payload = {
        "source_language": profile.code,
        "source_language_name": profile.display_name,
        "stream_index": result["stream"].get("index"),
        "codec_name": result["codec_name"],
        "title": result["title"],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"source language: {profile.display_name} ({profile.code})")
        print(f"subtitle stream index: {payload['stream_index']}")
        print(f"codec: {payload['codec_name']}")


if __name__ == "__main__":
    main()
