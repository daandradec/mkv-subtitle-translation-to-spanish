#!/usr/bin/env python3
import argparse
import json
import re
import secrets
from pathlib import Path


def semantic_prefix(stem, max_length=24):
    words = []
    for raw_word in stem.split(" "):
        word = re.sub(r"[^A-Za-z0-9]+", "", raw_word)
        if word:
            words.append(word)
    if not words:
        words = ["video"]

    selected = ""
    for word in words:
        candidate = word if not selected else f"{selected}-{word}"
        if len(candidate) <= max_length:
            selected = candidate
            continue
        if not selected:
            selected = word[:max_length]
        break
    return selected or "video"


def make_workspace_id(input_mkv, suffix="", max_prefix_length=24):
    stem = Path(input_mkv).stem
    prefix = semantic_prefix(stem, max_prefix_length)
    suffix = suffix or secrets.token_hex(3).upper()
    suffix = re.sub(r"[^A-Za-z0-9]", "", suffix).upper()[:6].ljust(6, "0")
    return f"{prefix}-{suffix}"


def build_workspace(input_mkv, workspace_id=""):
    workspace_id = workspace_id or make_workspace_id(input_mkv)
    stem = Path(input_mkv).stem
    output_dir = Path("output") / workspace_id
    return {
        "workspace_id": workspace_id,
        "subtitle_work_dir": str(Path("subtitle_work") / workspace_id),
        "translations_dir": str(Path("translations") / workspace_id),
        "output_dir": str(output_dir),
        "source_ass": str(Path("subtitle_work") / workspace_id / f"{stem}.source.ass"),
        "spanish_ass": str(output_dir / f"{stem}.spa.ass"),
        "tv_safe_srt": str(output_dir / f"{stem}.spa.srt"),
        "normalization_report": str(Path("subtitle_work") / workspace_id / "spanish_normalization_report.json"),
        "output_mkv": str(output_dir / f"{stem}.spa.mkv"),
    }


def main():
    parser = argparse.ArgumentParser(description="Create deterministic per-run subtitle workspace paths.")
    parser.add_argument("--input-mkv", required=True)
    parser.add_argument("--workspace-id", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload = build_workspace(args.input_mkv, args.workspace_id)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
