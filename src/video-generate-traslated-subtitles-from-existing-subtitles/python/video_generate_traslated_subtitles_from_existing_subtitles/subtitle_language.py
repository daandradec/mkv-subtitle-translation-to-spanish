#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

from video_toolkit.languages import (
    SUPPORTED_LANGUAGE_NAMES,
    UnsupportedLanguageError,
    get_language_profile,
    normalize_language_code,
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


def run_mkvmerge(input_mkv):
    command = ["mkvmerge", "-J", str(input_mkv)]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def safe_profile_code(language):
    try:
        return normalize_language_code(language)
    except UnsupportedLanguageError:
        return ""


def is_text_subtitle_codec(codec_name, codec_id=""):
    codec_values = {codec_name.casefold(), codec_id.casefold()}
    text_codec_ids = {"s_text/ass", "s_text/ssa", "s_text/utf8", "s_text/webvtt"}
    return bool(codec_values & TEXT_SUBTITLE_CODECS) or bool(codec_values & text_codec_ids)


def is_forced_track(candidate):
    title = candidate.get("title", "").casefold()
    return bool(candidate.get("forced")) or "forced" in title or "forzado" in title


def is_cc_track(candidate):
    title = candidate.get("title", "").casefold()
    return "cc" in title or "closed caption" in title or "sdh" in title


def preferred_audio_languages(mkvmerge_data):
    audio_tracks = [track for track in mkvmerge_data.get("tracks", []) if track.get("type") == "audio"]
    defaults = [track for track in audio_tracks if track.get("properties", {}).get("default_track")]
    ordered = defaults or audio_tracks
    result = []
    for track in ordered:
        props = track.get("properties", {})
        for raw in (props.get("language_ietf"), props.get("language")):
            code = safe_profile_code(raw or "")
            if code and code not in result:
                result.append(code)
    return result


def inspect_subtitle_candidates(input_mkv):
    ffprobe_data = run_ffprobe(input_mkv)
    mkvmerge_data = run_mkvmerge(input_mkv)
    subtitle_streams = ffprobe_data.get("streams", [])
    subtitle_tracks = [track for track in mkvmerge_data.get("tracks", []) if track.get("type") == "subtitles"]
    audio_preferences = preferred_audio_languages(mkvmerge_data)
    candidates = []

    for subtitle_ordinal, track in enumerate(subtitle_tracks):
        props = track.get("properties", {})
        mkv_track_id = int(track.get("id", -1))
        stream = subtitle_streams[subtitle_ordinal] if subtitle_ordinal < len(subtitle_streams) else {}
        stream_index = int(stream.get("index", mkv_track_id))
        codec_name = stream.get("codec_name", "")
        codec_id = props.get("codec_id", "")
        language_raw = props.get("language_ietf") or props.get("language") or stream.get("tags", {}).get("language", "")
        profile_code = safe_profile_code(language_raw)
        title = props.get("track_name") or stream.get("tags", {}).get("title", "")
        candidate = {
            "stream_index": stream_index,
            "mkv_track_id": mkv_track_id,
            "codec_name": codec_name,
            "codec_id": codec_id,
            "language_raw": language_raw,
            "source_language": profile_code,
            "title": title,
            "default": bool(props.get("default_track")),
            "forced": bool(props.get("forced_track")),
            "event_count": int(props.get("tag_number_of_frames") or props.get("num_index_entries") or 0),
            "duration": props.get("tag_duration", ""),
            "textual": is_text_subtitle_codec(codec_name, codec_id),
            "supported": bool(profile_code),
        }
        forced = is_forced_track(candidate)
        cc = is_cc_track(candidate)
        audio_rank = audio_preferences.index(profile_code) if profile_code in audio_preferences else 99
        candidate["forced_like"] = forced
        candidate["cc_like"] = cc
        candidate["score"] = (
            0 if candidate["supported"] else -100_000,
            0 if candidate["textual"] else -100_000,
            0 if forced else 10_000,
            0 if cc else 1_000,
            candidate["event_count"],
            500 - audio_rank if audio_rank != 99 else 0,
            100 if candidate["default"] else 0,
        )
        candidates.append(candidate)

    return {
        "audio_language_preferences": audio_preferences,
        "candidates": candidates,
    }


def choose_best_subtitle_candidate(inventory):
    candidates = [
        candidate
        for candidate in inventory["candidates"]
        if candidate["supported"] and candidate["textual"]
    ]
    if not candidates:
        if inventory["candidates"]:
            raise ValueError(
                "No se encontró una pista de subtítulos textual con idioma soportado para traducir a español."
            )
        raise ValueError("No se encontraron subtítulos incrustados en el archivo original para traducir a español.")

    default_candidates = [candidate for candidate in candidates if candidate["default"]]
    if default_candidates:
        candidates = default_candidates
        selection_reason = (
            "Se eligió una pista textual soportada marcada como default. "
            "Si quieres otra pista, pasa -SourceSubtitleStreamIndex."
        )
    else:
        selection_reason = (
            "No había pista default textual soportada; se eligió la mejor candidata por cobertura, "
            "idioma y descarte de pistas forced/CC."
        )

    non_forced = [candidate for candidate in candidates if not candidate["forced_like"]]
    if non_forced:
        candidates = non_forced
    non_cc = [candidate for candidate in candidates if not candidate["cc_like"]]
    if non_cc:
        candidates = non_cc

    selected = max(candidates, key=lambda candidate: candidate["score"])
    selected["selection_reason"] = selection_reason
    return selected, inventory


def select_best_subtitle_stream(input_mkv):
    inventory = inspect_subtitle_candidates(input_mkv)
    return choose_best_subtitle_candidate(inventory)


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
    selected = None
    if stream_index is None:
        selected, _inventory = select_best_subtitle_stream(input_mkv)
        stream_index = selected["stream_index"]
    else:
        inventory = inspect_subtitle_candidates(input_mkv)
        selected = next(
            (
                candidate
                for candidate in inventory["candidates"]
                if candidate["stream_index"] == stream_index
            ),
            None,
        )
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
        "mkv_track_id": selected["mkv_track_id"] if selected else stream_index,
        "detected_language": detected,
        "codec_name": codec_name,
        "title": tags.get("title", ""),
    }


def main():
    parser = argparse.ArgumentParser(description="Validate subtitle language against the supported source-language list.")
    parser.add_argument("--input-mkv", required=True)
    parser.add_argument("--stream-index", type=int)
    parser.add_argument("--language-override", default="")
    parser.add_argument("--list-candidates", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        if args.list_candidates:
            inventory = inspect_subtitle_candidates(Path(args.input_mkv))
            if args.json:
                print(json.dumps(inventory, ensure_ascii=True, indent=2))
            else:
                for candidate in inventory["candidates"]:
                    print(
                        f"{candidate['stream_index']}: {candidate['source_language'] or candidate['language_raw']} "
                        f"{candidate['codec_name'] or candidate['codec_id']} "
                        f"default={candidate['default']} forced={candidate['forced_like']} "
                        f"events={candidate['event_count']} title={candidate['title']}"
                    )
            return
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
        "mkv_track_id": result["mkv_track_id"],
        "codec_name": result["codec_name"],
        "title": result["title"],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    else:
        print(f"source language: {profile.display_name} ({profile.code})")
        print(f"subtitle stream index: {payload['stream_index']}")
        print(f"codec: {payload['codec_name']}")


if __name__ == "__main__":
    main()
