#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from video_toolkit.workspace_ids import output_folder_name


def build_transcription_workspace(input_video):
    output_name = output_folder_name(input_video)
    stem = Path(input_video).stem
    output_dir = Path("outputs") / output_name
    debug_dir = output_dir / "debug" / "video-generate-new-subtitles-from-audio"
    whisper_output_dir = debug_dir / "whisper"
    postprocess_dir = debug_dir / "postprocess"
    reports_dir = debug_dir / "reports"
    audio_wav = debug_dir / "audio" / f"{stem}.audio.wav"
    return {
        "output_name": output_name,
        "debug_dir": str(debug_dir),
        "output_dir": str(output_dir),
        "whisper_output_dir": str(whisper_output_dir),
        "postprocess_dir": str(postprocess_dir),
        "audio_wav": str(audio_wav),
        "transcribed_srt": str(postprocess_dir / f"{stem}.transcribed.srt"),
        "transcribed_mkv": str(output_dir / f"{stem}.transcribed.mkv"),
        "exported_ass": str(output_dir / "sidecars" / f"{stem}.transcribed.ass"),
        "transcription_report": str(reports_dir / "transcription_report.json"),
        "remux_validation_report": str(reports_dir / "remux_validation.json"),
    }


def main():
    parser = argparse.ArgumentParser(description="Create per-run transcription workspace paths.")
    parser.add_argument("--input-video", "--input-mkv", dest="input_video", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload = build_transcription_workspace(args.input_video)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
