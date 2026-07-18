#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from subtitle_workspace import make_workspace_id


def unique_workspace_id(input_video, output_root="output", workspace_id=""):
    if workspace_id:
        return workspace_id

    output_root = Path(output_root)
    for _ in range(128):
        candidate = make_workspace_id(input_video)
        if not (output_root / candidate).exists():
            return candidate
    raise RuntimeError("No se pudo generar un workspace id unico despues de varios intentos.")


def build_text_transcription_workspace(input_video, workspace_id="", output_root="output"):
    workspace_id = unique_workspace_id(input_video, output_root=output_root, workspace_id=workspace_id)
    stem = Path(input_video).stem
    subtitle_work_dir = Path("subtitle_work") / workspace_id
    output_dir = Path(output_root) / workspace_id
    audio_wav = subtitle_work_dir / "text-transcription" / f"{stem}.wav"
    return {
        "workspace_id": workspace_id,
        "subtitle_work_dir": str(subtitle_work_dir),
        "text_work_dir": str(subtitle_work_dir / "text-transcription"),
        "output_dir": str(output_dir),
        "audio_wav": str(audio_wav),
        "audio_stem": stem,
        "json": str(output_dir / f"{stem}.json"),
        "srt": str(output_dir / f"{stem}.srt"),
        "vtt": str(output_dir / f"{stem}.vtt"),
        "txt": str(output_dir / f"{stem}.txt"),
        "tsv": str(output_dir / f"{stem}.tsv"),
        "markdown": str(output_dir / f"{stem}.md"),
        "report": str(output_dir / "text_transcription_report.json"),
    }


def main():
    parser = argparse.ArgumentParser(description="Create per-video text transcription workspace paths.")
    parser.add_argument("--input-video", required=True)
    parser.add_argument("--workspace-id", default="")
    parser.add_argument("--output-root", default="output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload = build_text_transcription_workspace(
        args.input_video,
        workspace_id=args.workspace_id,
        output_root=args.output_root,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
