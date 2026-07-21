#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

from video_toolkit.workspace_ids import output_folder_name


MODEL_PATH = Path("models") / "voice-cleaner" / "std.rnnn"
TARGET_I = "-16.0"
TARGET_LRA = "9"
TARGET_TP = "-2.0"


PROFILE_SETTINGS = {
    "conservative": {
        "rnnoise_mix": "0.25",
        "afftdn_nr": "5",
        "afftdn_nf": "-36",
        "anlmdn_s": "0.000020",
        "gate_threshold": "0.006",
        "gate_ratio": "1.15",
        "gate_range": "0.18",
        "compressor_threshold": "0.16",
        "compressor_ratio": "1.35",
        "presence_2300": "0.9",
        "presence_3600": "0.7",
        "deesser_i": "0.08",
    },
    "balanced": {
        "rnnoise_mix": "0.35",
        "afftdn_nr": "8",
        "afftdn_nf": "-39",
        "anlmdn_s": "0.000030",
        "gate_threshold": "0.010",
        "gate_ratio": "1.35",
        "gate_range": "0.32",
        "compressor_threshold": "0.13",
        "compressor_ratio": "1.55",
        "presence_2300": "1.2",
        "presence_3600": "1.0",
        "deesser_i": "0.10",
    },
    "asr": {
        "rnnoise_mix": "0.45",
        "afftdn_nr": "11",
        "afftdn_nf": "-42",
        "anlmdn_s": "0.000040",
        "gate_threshold": "0.014",
        "gate_ratio": "1.65",
        "gate_range": "0.48",
        "compressor_threshold": "0.11",
        "compressor_ratio": "1.80",
        "presence_2300": "1.6",
        "presence_3600": "1.3",
        "deesser_i": "0.12",
    },
}


def build_voice_cleaner_workspace(input_video):
    output_name = output_folder_name(input_video)
    stem = Path(input_video).stem
    output_dir = Path("output") / output_name
    debug_dir = output_dir / "debug" / "video-voice-cleaner"
    work_dir = debug_dir / "work"
    return {
        "output_name": output_name,
        "debug_dir": str(debug_dir),
        "work_dir": str(work_dir),
        "output_dir": str(output_dir),
        "premaster_flac": str(work_dir / f"{stem}.voice-cleaned.premaster.flac"),
        "clean_flac": str(output_dir / f"{stem}.voice-cleaned.flac"),
        "output_mkv": str(output_dir / f"{stem}.voice-cleaned.mkv"),
        "report": str(debug_dir / "reports" / "voice_cleaner_report.json"),
        "samples_dir": str(debug_dir / "samples"),
    }


def validate_profile(profile):
    profile = (profile or "conservative").casefold()
    if profile not in PROFILE_SETTINGS:
        allowed = ", ".join(sorted(PROFILE_SETTINGS))
        raise ValueError(f"Unsupported voice cleaner profile: {profile}. Use one of: {allowed}.")
    return profile


def ffmpeg_filter_path(path):
    return str(path).replace("\\", "/").replace(":", "\\:")


def voice_filter_chain(profile="conservative", model_path=MODEL_PATH):
    profile = validate_profile(profile)
    settings = PROFILE_SETTINGS[profile]
    model = ffmpeg_filter_path(model_path)
    filters = [
        "volume=0.95",
        "adeclip=window=55:overlap=75:arorder=8:threshold=9",
        "highpass=f=70",
        "lowpass=f=13500",
        f"arnndn=m={model}:mix={settings['rnnoise_mix']}",
        (
            "afftdn="
            f"nr={settings['afftdn_nr']}:"
            f"nf={settings['afftdn_nf']}:"
            "tn=1:tr=0:ad=0.35:fo=0.7:gs=4"
        ),
        f"anlmdn=s={settings['anlmdn_s']}:p=0.002:r=0.008:m=9",
        (
            "agate="
            f"threshold={settings['gate_threshold']}:"
            f"ratio={settings['gate_ratio']}:"
            "attack=18:release=240:"
            f"range={settings['gate_range']}:"
            "knee=3:detection=rms:link=average"
        ),
        "equalizer=f=160:t=q:w=1.0:g=-0.8",
        "equalizer=f=300:t=q:w=1.2:g=-0.6",
        f"equalizer=f=2300:t=q:w=1.0:g={settings['presence_2300']}",
        f"equalizer=f=3600:t=q:w=1.2:g={settings['presence_3600']}",
        f"deesser=i={settings['deesser_i']}:m=0.22:f=0.60",
        (
            "acompressor="
            f"threshold={settings['compressor_threshold']}:"
            f"ratio={settings['compressor_ratio']}:"
            "attack=15:release=190:makeup=1.03:knee=3:detection=rms:link=average"
        ),
        "alimiter=limit=0.82:attack=5:release=120:level=false",
        "aresample=48000",
    ]
    return ",".join(filters)


def extract_loudnorm_json(text):
    matches = re.findall(r"\{\s*\"input_i\".*?\}", text or "", flags=re.S)
    if not matches:
        raise ValueError("Could not find loudnorm JSON in ffmpeg output.")
    return json.loads(matches[-1])


def loudnorm_second_pass_filter(stats, target_i=TARGET_I, target_lra=TARGET_LRA, target_tp=TARGET_TP):
    return (
        f"loudnorm=I={target_i}:LRA={target_lra}:TP={target_tp}"
        f":measured_I={stats['input_i']}"
        f":measured_LRA={stats['input_lra']}"
        f":measured_TP={stats['input_tp']}"
        f":measured_thresh={stats['input_thresh']}"
        f":offset={stats['target_offset']}"
        ":linear=true:print_format=summary,"
        "alimiter=limit=0.82:attack=5:release=120:level=false,aresample=48000"
    )


def main():
    parser = argparse.ArgumentParser(description="Voice cleaner helpers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    workspace = subparsers.add_parser("workspace", help="Create voice cleaner workspace paths.")
    workspace.add_argument("--input-video", required=True)
    workspace.add_argument("--json", action="store_true")

    chain = subparsers.add_parser("chain", help="Build FFmpeg voice filter chain.")
    chain.add_argument("--profile", choices=sorted(PROFILE_SETTINGS), default="conservative")
    chain.add_argument("--model-path", default=str(MODEL_PATH))
    chain.add_argument("--json", action="store_true")

    loudnorm = subparsers.add_parser("loudnorm-second-pass", help="Build loudnorm second pass filter.")
    loudnorm.add_argument("--stats-json", required=True)
    loudnorm.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "workspace":
        payload = build_voice_cleaner_workspace(args.input_video)
    elif args.command == "chain":
        payload = {
            "profile": args.profile,
            "model_path": args.model_path,
            "filter": voice_filter_chain(args.profile, Path(args.model_path)),
        }
    elif args.command == "loudnorm-second-pass":
        stats = json.loads(Path(args.stats_json).read_text(encoding="utf-8-sig"))
        payload = {"filter": loudnorm_second_pass_filter(stats)}
    else:
        raise SystemExit(f"Unsupported command: {args.command}")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
