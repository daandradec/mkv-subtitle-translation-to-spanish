#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from subtitle_workspace import make_workspace_id


def build_transcription_workspace(input_video, workspace_id=""):
    workspace_id = workspace_id or make_workspace_id(input_video)
    stem = Path(input_video).stem
    subtitle_work_dir = Path("subtitle_work") / workspace_id
    output_dir = Path("output") / workspace_id
    whisper_output_dir = subtitle_work_dir / "whisper"
    audio_wav = subtitle_work_dir / f"{stem}.audio.wav"
    return {
        "workspace_id": workspace_id,
        "subtitle_work_dir": str(subtitle_work_dir),
        "output_dir": str(output_dir),
        "whisper_output_dir": str(whisper_output_dir),
        "audio_wav": str(audio_wav),
        "transcribed_srt": str(output_dir / f"{stem}.transcribed.srt"),
        "transcribed_ass": str(output_dir / f"{stem}.transcribed.ass"),
        "transcribed_mkv": str(output_dir / f"{stem}.transcribed.mkv"),
        "transcription_report": str(subtitle_work_dir / "transcription_report.json"),
    }


def main():
    parser = argparse.ArgumentParser(description="Create per-run transcription workspace paths.")
    parser.add_argument("--input-video", "--input-mkv", dest="input_video", required=True)
    parser.add_argument("--workspace-id", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload = build_transcription_workspace(args.input_video, args.workspace_id)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
