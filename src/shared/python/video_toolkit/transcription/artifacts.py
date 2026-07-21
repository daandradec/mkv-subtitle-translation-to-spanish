"""Neutral helpers for locating and inspecting transcription backend outputs."""

import json
from pathlib import Path


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

