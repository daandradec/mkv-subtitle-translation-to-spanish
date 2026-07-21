#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from video_toolkit.workspace_ids import output_folder_name


def build_text_transcription_workspace(input_video, output_root="output"):
    output_name = output_folder_name(input_video)
    stem = Path(input_video).stem
    output_dir = Path(output_root) / output_name
    debug_dir = output_dir / "debug" / "video-text-agent-transcription"
    text_work_dir = debug_dir / "audio"
    whisper_dir = debug_dir / "whisper"
    whisper_raw_dir = whisper_dir / "raw"
    whisper_postprocess_dir = whisper_dir / "postprocess"
    audio_wav = text_work_dir / f"{stem}.wav"
    return {
        "output_name": output_name,
        "debug_dir": str(debug_dir),
        "text_work_dir": str(text_work_dir),
        "whisper_dir": str(whisper_dir),
        "whisper_raw_dir": str(whisper_raw_dir),
        "whisper_postprocess_dir": str(whisper_postprocess_dir),
        "output_dir": str(output_dir),
        "audio_wav": str(audio_wav),
        "audio_stem": stem,
        "json": str(whisper_raw_dir / f"{stem}.json"),
        "srt": str(output_dir / f"{stem}.srt"),
        "vtt": str(whisper_postprocess_dir / f"{stem}.vtt"),
        "txt": str(whisper_postprocess_dir / f"{stem}.txt"),
        "tsv": str(whisper_raw_dir / f"{stem}.tsv"),
        "markdown": str(output_dir / f"{stem}.md"),
        "report": str(debug_dir / "reports" / "text_transcription_report.json"),
    }


def main():
    parser = argparse.ArgumentParser(description="Create per-video text transcription workspace paths.")
    parser.add_argument("--input-video", required=True)
    parser.add_argument("--output-root", default="output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload = build_text_transcription_workspace(
        args.input_video,
        output_root=args.output_root,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
