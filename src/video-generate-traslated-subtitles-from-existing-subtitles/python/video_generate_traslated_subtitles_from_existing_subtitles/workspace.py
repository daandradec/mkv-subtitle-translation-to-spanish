#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from video_toolkit.workspace_ids import output_folder_name


def build_workspace(input_mkv):
    output_name = output_folder_name(input_mkv)
    stem = Path(input_mkv).stem
    output_dir = Path("outputs") / output_name
    debug_dir = output_dir / "debug" / "video-generate-traslated-subtitles-from-existing-subtitles"
    subtitles_dir = debug_dir / "subtitles"
    source_dir = subtitles_dir / "source"
    generated_dir = subtitles_dir / "generated"
    reports_dir = debug_dir / "reports"
    return {
        "output_name": output_name,
        "debug_dir": str(debug_dir),
        "subtitles_dir": str(subtitles_dir),
        "reports_dir": str(reports_dir),
        "translations_dir": str(debug_dir / "translations"),
        "output_dir": str(output_dir),
        "source_ass": str(source_dir / f"{stem}.source.ass"),
        "spanish_ass": str(generated_dir / f"{stem}.spa.ass"),
        "tv_safe_srt": str(generated_dir / f"{stem}.spa.srt"),
        "normalization_report": str(reports_dir / "spanish_normalization_report.json"),
        "remux_validation_report": str(reports_dir / "remux_validation_report.json"),
        "translation_checkpoint": str(debug_dir / "checkpoints" / "translation_checkpoint.json"),
        "output_mkv": str(output_dir / f"{stem}.spa.mkv"),
    }


def main():
    parser = argparse.ArgumentParser(description="Create deterministic per-video subtitle workspace paths.")
    parser.add_argument("--input-mkv", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload = build_workspace(args.input_mkv)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
