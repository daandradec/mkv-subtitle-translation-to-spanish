import argparse
import json
import shutil
import subprocess
from collections import Counter
from pathlib import Path
import re
from statistics import median
import tempfile

from video_toolkit.subtitles.text import convert_text_subtitle_to_ass


SRT_TIME_RE = re.compile(
    r"(?m)^(?P<hours>\d{1,3}):(?P<minutes>\d{2}):(?P<seconds>\d{2})[,.](?P<milliseconds>\d{3})\s+-->"
)


def _run(command):
    completed = subprocess.run(
        [str(value) for value in command],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(
            f"Command failed with exit code {completed.returncode}: {' '.join(map(str, command))}\n{detail}"
        )
    return completed


def _run_json(command):
    completed = _run(command)
    payload = completed.stdout.lstrip("\ufeff").strip()
    if not payload:
        raise RuntimeError(f"Command returned no JSON: {' '.join(map(str, command))}")
    return json.loads(payload)


def probe_media(path):
    return _run_json(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=format_name,start_time,duration:stream=index,codec_type,codec_name,start_time,duration:stream_disposition=default,forced:stream_tags=language,title",
            "-of",
            "json",
            str(path),
        ]
    )


def remux_strategy(format_name):
    names = {part.strip().lower() for part in (format_name or "").split(",") if part.strip()}
    return "mkvmerge-native" if names.intersection({"matroska", "webm"}) else "ffmpeg-shared-timeline"


def parse_srt_start_times(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    starts = []
    for match in SRT_TIME_RE.finditer(text):
        hours = int(match.group("hours"))
        minutes = int(match.group("minutes"))
        seconds = int(match.group("seconds"))
        milliseconds = int(match.group("milliseconds"))
        starts.append(hours * 3600 + minutes * 60 + seconds + milliseconds / 1000)
    if not starts:
        raise RuntimeError(f"No subtitle cue timestamps were found in: {path}")
    return starts


def build_ffmpeg_remux_command(input_video, srt_path, output_mkv, language, title, source_subtitle_count):
    command = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(input_video),
        "-i",
        str(srt_path),
        "-map",
        "0",
        "-map",
        "1:0",
        "-map_metadata",
        "0",
        "-map_chapters",
        "0",
        "-c",
        "copy",
    ]
    for subtitle_index in range(source_subtitle_count):
        command.extend([f"-disposition:s:{subtitle_index}", "-default"])
    command.extend(
        [
            f"-metadata:s:s:{source_subtitle_count}",
            f"language={language}",
            f"-metadata:s:s:{source_subtitle_count}",
            f"title={title}",
            f"-disposition:s:{source_subtitle_count}",
            "default",
            str(output_mkv),
        ]
    )
    return command


def build_mkvmerge_remux_command(input_video, srt_path, output_mkv, language, title, source_tracks):
    command = ["mkvmerge", "--output", str(output_mkv)]
    for track in source_tracks:
        if track.get("type") == "subtitles":
            command.extend(["--default-track-flag", f"{int(track['id'])}:no"])
    command.extend(
        [
            str(input_video),
            "--language",
            f"0:{language}",
            "--track-name",
            f"0:{title}",
            "--default-track-flag",
            "0:yes",
            str(srt_path),
        ]
    )
    return command


def _stream_counts(probe):
    return Counter(stream.get("codec_type", "unknown") for stream in probe.get("streams", []))


def _subtitle_packet_times(output_mkv, stream_index):
    probe = _run_json(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            str(stream_index),
            "-show_packets",
            "-show_entries",
            "packet=pts_time",
            "-of",
            "json",
            str(output_mkv),
        ]
    )
    return [float(packet["pts_time"]) for packet in probe.get("packets", []) if "pts_time" in packet]


def export_synchronized_ass(output_mkv, output_ass, subtitle_stream_index, title):
    output_mkv = Path(output_mkv).resolve()
    output_ass = Path(output_ass).resolve()
    if output_ass.parent == output_mkv.parent:
        raise RuntimeError(
            "The exported ASS must be stored in a separate sidecars directory so players do not auto-load it "
            "beside the MKV."
        )

    embedded_starts = _subtitle_packet_times(output_mkv, subtitle_stream_index)
    if not embedded_starts:
        raise RuntimeError("The embedded transcription track has no subtitle packets to export.")

    output_ass.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="video-subtitle-ass-export-") as temporary_dir:
        extracted_srt = Path(temporary_dir) / "embedded-transcription.srt"
        _run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-copyts",
                "-i",
                str(output_mkv),
                "-map",
                f"0:{subtitle_stream_index}",
                "-c:s",
                "srt",
                str(extracted_srt),
            ]
        )
        extracted_starts = parse_srt_start_times(extracted_srt)
        if len(extracted_starts) != len(embedded_starts):
            raise RuntimeError(
                "Synchronized ASS export cue count mismatch: "
                f"embedded={len(embedded_starts)}, extracted={len(extracted_starts)}."
            )
        timing_deltas = [abs(extracted - embedded) for extracted, embedded in zip(extracted_starts, embedded_starts)]
        maximum_delta = max(timing_deltas)
        if maximum_delta > 0.002:
            raise RuntimeError(
                "Synchronized ASS export changed embedded timestamps; "
                f"maximum delta is {maximum_delta:.6f} seconds."
            )
        ass_result = convert_text_subtitle_to_ass(
            extracted_srt,
            output_ass,
            title=title,
            margin_l=192,
            margin_r=192,
        )

    if ass_result["written_dialogues"] != len(embedded_starts):
        raise RuntimeError(
            "Synchronized ASS dialogue count mismatch: "
            f"embedded={len(embedded_starts)}, ASS={ass_result['written_dialogues']}."
        )
    return {
        "status": "pass",
        "path": str(output_ass),
        "source": "embedded-transcription-track",
        "subtitle_stream_index": subtitle_stream_index,
        "cue_count": len(embedded_starts),
        "first_cue_seconds": round(embedded_starts[0], 6),
        "timestamp_max_delta_seconds": round(maximum_delta, 6),
    }


def validate_remux(
    input_video,
    srt_path,
    output_mkv,
    language,
    title,
    strategy,
    source_probe=None,
):
    source_probe = source_probe or probe_media(input_video)
    output_probe = probe_media(output_mkv)
    source_counts = _stream_counts(source_probe)
    output_counts = _stream_counts(output_probe)
    expected_counts = source_counts.copy()
    expected_counts["subtitle"] += 1
    if output_counts != expected_counts:
        raise RuntimeError(
            f"Remux stream preservation failed. Expected {dict(expected_counts)}, found {dict(output_counts)}."
        )

    output_subtitles = [stream for stream in output_probe.get("streams", []) if stream.get("codec_type") == "subtitle"]
    target = output_subtitles[-1]
    tags = target.get("tags") or {}
    disposition = target.get("disposition") or {}
    if (tags.get("language") or "").lower() != language.lower():
        raise RuntimeError(
            f"Transcribed subtitle language mismatch: expected {language}, found {tags.get('language')}."
        )
    if tags.get("title") != title:
        raise RuntimeError(f"Transcribed subtitle title mismatch: expected {title!r}, found {tags.get('title')!r}.")
    if int(disposition.get("default", 0)) != 1:
        raise RuntimeError("The transcribed subtitle track is not marked default.")
    for original in output_subtitles[:-1]:
        if int((original.get("disposition") or {}).get("default", 0)) == 1:
            raise RuntimeError("An original subtitle track is still marked default.")

    source_starts = parse_srt_start_times(srt_path)
    embedded_starts = _subtitle_packet_times(output_mkv, int(target["index"]))
    if len(source_starts) != len(embedded_starts):
        raise RuntimeError(
            f"Embedded subtitle cue count mismatch: expected {len(source_starts)}, found {len(embedded_starts)}."
        )
    shifts = [embedded - source for source, embedded in zip(source_starts, embedded_starts)]
    shift_spread = max(shifts) - min(shifts)
    if shift_spread > 0.005:
        raise RuntimeError(
            f"Subtitle timeline transformation is not uniform; spread is {shift_spread:.6f} seconds."
        )

    return {
        "status": "pass",
        "strategy": strategy,
        "source_format": (source_probe.get("format") or {}).get("format_name", ""),
        "source_stream_counts": dict(source_counts),
        "output_stream_counts": dict(output_counts),
        "subtitle_stream_index": int(target["index"]),
        "subtitle_codec": target.get("codec_name", ""),
        "subtitle_language": tags.get("language", ""),
        "subtitle_title": tags.get("title", ""),
        "subtitle_default": int(disposition.get("default", 0)),
        "cue_count": len(source_starts),
        "timeline_shift_seconds": round(median(shifts), 6),
        "timeline_shift_spread_seconds": round(shift_spread, 6),
        "source_duration_seconds": (source_probe.get("format") or {}).get("duration"),
        "output_duration_seconds": (output_probe.get("format") or {}).get("duration"),
    }


def remux_transcription(
    input_video,
    srt_path,
    output_mkv,
    language,
    title,
    report_path=None,
    export_ass_path=None,
):
    input_video = Path(input_video).resolve()
    srt_path = Path(srt_path).resolve()
    output_mkv = Path(output_mkv).resolve()
    report_path = Path(report_path).resolve() if report_path else None
    source_probe = probe_media(input_video)
    format_name = (source_probe.get("format") or {}).get("format_name", "")
    strategy = remux_strategy(format_name)
    source_subtitle_count = _stream_counts(source_probe)["subtitle"]
    output_mkv.parent.mkdir(parents=True, exist_ok=True)

    if strategy == "mkvmerge-native":
        if not shutil.which("mkvmerge"):
            raise RuntimeError("mkvmerge not found in PATH; it is required for native Matroska/WebM remuxing.")
        identification = _run_json(["mkvmerge", "-J", str(input_video)])
        command = build_mkvmerge_remux_command(
            input_video,
            srt_path,
            output_mkv,
            language,
            title,
            identification.get("tracks", []),
        )
    else:
        command = build_ffmpeg_remux_command(
            input_video,
            srt_path,
            output_mkv,
            language,
            title,
            source_subtitle_count,
        )

    _run(command)
    report = validate_remux(
        input_video,
        srt_path,
        output_mkv,
        language,
        title,
        strategy,
        source_probe=source_probe,
    )
    report["command"] = command
    if export_ass_path:
        report["ass_export"] = export_synchronized_ass(
            output_mkv,
            export_ass_path,
            report["subtitle_stream_index"],
            title,
        )
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["report"] = str(report_path)
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Remux a transcription track into MKV with container-aware timeline normalization."
    )
    parser.add_argument("--input-video", required=True)
    parser.add_argument("--srt", required=True)
    parser.add_argument("--output-mkv", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--report")
    parser.add_argument(
        "--export-ass-file-subtitles",
        metavar="PATH",
        help="Export an ASS sidecar from the normalized subtitle track embedded in the final MKV.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = remux_transcription(
        args.input_video,
        args.srt,
        args.output_mkv,
        args.language,
        args.title,
        report_path=args.report,
        export_ass_path=args.export_ass_file_subtitles,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(f"strategy: {report['strategy']}")
        print(f"timeline shift: {report['timeline_shift_seconds']:.6f} seconds")
        print(f"report: {report.get('report', '')}")


if __name__ == "__main__":
    main()
