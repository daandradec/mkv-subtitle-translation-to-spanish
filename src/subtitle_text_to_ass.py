#!/usr/bin/env python3
"""
Convert extracted text subtitle tracks (SRT or WebVTT) into a simple ASS file.

This module is intentionally standalone so existing ASS-oriented workflow stages can
consume SRT/VTT input tracks after extraction without changing their parser contracts.

Example:
    python src/subtitle_text_to_ass.py --input input.srt --output subtitle_work/input.ass
    python src/subtitle_text_to_ass.py --input input.vtt --output subtitle_work/input.ass --format vtt
"""

import argparse
import html
import re
from dataclasses import dataclass
from pathlib import Path


ASS_HEADER_TEMPLATE = """[Script Info]
Title: {title}
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {play_res_x}
PlayResY: {play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H99000000,0,0,0,0,100,100,0,0,1,2,0,2,{margin_l},{margin_r},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


TIMESTAMP_RE = re.compile(
    r"(?P<start>(?:\d{1,2}:)?\d{1,2}:\d{2}[\.,]\d{3})\s+-->\s+"
    r"(?P<end>(?:\d{1,2}:)?\d{1,2}:\d{2}[\.,]\d{3})(?:\s+.*)?$"
)


@dataclass(frozen=True)
class TextCue:
    start_ms: int
    end_ms: int
    text: str
    identifier: str = ""


def detect_format(path, explicit_format="auto"):
    if explicit_format != "auto":
        return explicit_format.lower()
    suffix = path.suffix.lower()
    if suffix == ".srt":
        return "srt"
    if suffix in {".vtt", ".webvtt"}:
        return "vtt"
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:512]
    if sample.lstrip().startswith("WEBVTT"):
        return "vtt"
    return "srt"


def parse_timestamp(value):
    value = value.replace(",", ".")
    parts = value.split(":")
    if len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    elif len(parts) == 3:
        hours, minutes, seconds = parts
    else:
        raise ValueError(f"Invalid subtitle timestamp: {value}")
    whole_seconds, milliseconds = seconds.split(".")
    return (
        int(hours) * 3_600_000
        + int(minutes) * 60_000
        + int(whole_seconds) * 1_000
        + int(milliseconds[:3].ljust(3, "0"))
    )


def ms_to_ass_time(value):
    hours, remainder = divmod(value, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    centiseconds = round(milliseconds / 10)
    if centiseconds == 100:
        seconds += 1
        centiseconds = 0
    if seconds == 60:
        minutes += 1
        seconds = 0
    if minutes == 60:
        hours += 1
        minutes = 0
    return f"{hours}:{minutes:02}:{seconds:02}.{centiseconds:02}"


def clean_cue_text(lines):
    text = "\n".join(line.strip() for line in lines).strip()
    if not text:
        return ""
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(?:c|i|b|u|ruby|rt|v|lang)(?:\.[^ >]+)?(?:\s+[^>]*)?>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace("\ufeff", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def parse_srt_blocks(text):
    blocks = re.split(r"\n\s*\n", text.strip())
    for block in blocks:
        lines = [line.rstrip("\r") for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        identifier = ""
        timing_index = 0
        if "-->" not in lines[0] and len(lines) > 1:
            identifier = lines[0]
            timing_index = 1
        if timing_index >= len(lines):
            continue
        match = TIMESTAMP_RE.match(lines[timing_index].strip())
        if not match:
            continue
        text_value = clean_cue_text(lines[timing_index + 1 :])
        if text_value:
            yield TextCue(
                start_ms=parse_timestamp(match.group("start")),
                end_ms=parse_timestamp(match.group("end")),
                text=text_value,
                identifier=identifier,
            )


def parse_vtt_blocks(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.splitlines()
    if lines and lines[0].lstrip("\ufeff").startswith("WEBVTT"):
        lines = lines[1:]

    block = []
    for line in lines + [""]:
        stripped = line.strip()
        if not stripped:
            yield from parse_vtt_block(block)
            block = []
            continue
        if stripped.startswith(("NOTE", "STYLE", "REGION")):
            block = [stripped]
            continue
        block.append(line.rstrip("\n"))


def parse_vtt_block(lines):
    if not lines:
        return
    if lines[0].strip().startswith(("NOTE", "STYLE", "REGION")):
        return
    identifier = ""
    timing_index = 0
    if "-->" not in lines[0] and len(lines) > 1:
        identifier = lines[0].strip()
        timing_index = 1
    if timing_index >= len(lines):
        return
    match = TIMESTAMP_RE.match(lines[timing_index].strip())
    if not match:
        return
    text_value = clean_cue_text(lines[timing_index + 1 :])
    if text_value:
        yield TextCue(
            start_ms=parse_timestamp(match.group("start")),
            end_ms=parse_timestamp(match.group("end")),
            text=text_value,
            identifier=identifier,
        )


def parse_text_subtitles(path, subtitle_format="auto"):
    detected = detect_format(path, subtitle_format)
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if detected == "srt":
        cues = list(parse_srt_blocks(text.replace("\r\n", "\n").replace("\r", "\n")))
    elif detected == "vtt":
        cues = list(parse_vtt_blocks(text))
    else:
        raise ValueError(f"Unsupported subtitle format: {subtitle_format}")
    return [cue for cue in cues if cue.end_ms > cue.start_ms]


def escape_ass_text(text):
    text = text.replace("\\", "\\\\")
    text = text.replace("{", "(").replace("}", ")")
    text = text.replace("\n", r"\N")
    return text


def write_ass(
    cues,
    output_path,
    title="Converted text subtitles",
    play_res_x=1920,
    play_res_y=1080,
    font_name="Arial",
    font_size=54,
    margin_l=80,
    margin_r=80,
    margin_v=48,
):
    header = ASS_HEADER_TEMPLATE.format(
        title=title,
        play_res_x=play_res_x,
        play_res_y=play_res_y,
        font_name=font_name,
        font_size=font_size,
        margin_l=margin_l,
        margin_r=margin_r,
        margin_v=margin_v,
    )
    lines = [header.rstrip()]
    seen = set()
    for cue in sorted(cues, key=lambda item: (item.start_ms, item.end_ms, item.text)):
        key = (cue.start_ms, cue.end_ms, cue.text)
        if key in seen:
            continue
        seen.add(key)
        lines.append(
            "Dialogue: 0,{start},{end},Default,,0,0,0,,{text}".format(
                start=ms_to_ass_time(cue.start_ms),
                end=ms_to_ass_time(cue.end_ms),
                text=escape_ass_text(cue.text),
            )
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(seen)


def convert_text_subtitle_to_ass(input_path, output_path, subtitle_format="auto", **ass_options):
    cues = parse_text_subtitles(input_path, subtitle_format)
    written = write_ass(cues, output_path, **ass_options)
    return {"input_cues": len(cues), "written_dialogues": written}


def main():
    parser = argparse.ArgumentParser(description="Convert SRT/WebVTT subtitle files into simple ASS.")
    parser.add_argument("--input", required=True, help="Input .srt, .vtt, or .webvtt file extracted from a media container.")
    parser.add_argument("--output", required=True, help="Output .ass file for ASS-oriented processing stages.")
    parser.add_argument("--format", choices=["auto", "srt", "vtt"], default="auto")
    parser.add_argument("--title", default="Converted text subtitles")
    parser.add_argument("--play-res-x", type=int, default=1920)
    parser.add_argument("--play-res-y", type=int, default=1080)
    parser.add_argument("--font-name", default="Arial")
    parser.add_argument("--font-size", type=int, default=54)
    parser.add_argument("--margin-l", type=int, default=80)
    parser.add_argument("--margin-r", type=int, default=80)
    parser.add_argument("--margin-v", type=int, default=48)
    args = parser.parse_args()

    result = convert_text_subtitle_to_ass(
        Path(args.input),
        Path(args.output),
        subtitle_format=args.format,
        title=args.title,
        play_res_x=args.play_res_x,
        play_res_y=args.play_res_y,
        font_name=args.font_name,
        font_size=args.font_size,
        margin_l=args.margin_l,
        margin_r=args.margin_r,
        margin_v=args.margin_v,
    )
    print(f"input cues: {result['input_cues']}")
    print(f"written dialogue events: {result['written_dialogues']}")
    print(f"written: {args.output}")


if __name__ == "__main__":
    main()
