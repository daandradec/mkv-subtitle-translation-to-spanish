#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


DIALOGUE_PREFIX = "Dialogue: "


def parse_dialogue(line):
    if not line.startswith(DIALOGUE_PREFIX):
        return None
    fields = line[len(DIALOGUE_PREFIX) :].split(",", 9)
    if len(fields) != 10:
        return None
    return fields


def ass_time_to_ms(value):
    hours, minutes, seconds = value.split(":")
    whole_seconds, centiseconds = seconds.split(".")
    return (
        int(hours) * 3_600_000
        + int(minutes) * 60_000
        + int(whole_seconds) * 1_000
        + int(centiseconds.ljust(2, "0")[:2]) * 10
    )


def ms_to_srt_time(value):
    hours, remainder = divmod(value, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def strip_ass_text(raw):
    text = re.sub(r"\{[^{}]*\}", "", raw)
    text = text.replace(r"\N", "\n").replace(r"\n", "\n").replace(r"\h", " ")
    text = re.sub(r"\\[A-Za-z]+(?:\([^)]*\))?", "", text)
    lines = []
    for line in text.splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines).strip()


def looks_like_vector_path(text):
    normalized = text.replace("\n", " ").strip().lower()
    if not normalized:
        return False
    if not re.match(r"^[mlbns]\s+-?\d", normalized):
        return False
    path_commands = len(re.findall(r"\b[mlbns]\b", normalized))
    numbers = len(re.findall(r"-?\d+(?:\.\d+)?", normalized))
    letters = re.sub(r"\b[mlbns]\b", "", normalized)
    other_letters = re.findall(r"[a-zA-Z]", letters)
    return path_commands >= 2 and numbers >= 8 and not other_letters


def has_drawing_mode(raw):
    return bool(re.search(r"\\p[1-9]", raw))


def is_skippable(style, effect, raw, text):
    style_lower = style.lower()
    effect_lower = effect.lower()
    if "romaji" in style_lower or "kanji" in style_lower:
        return True
    if effect_lower in {"fx", "karaoke"}:
        return True
    if has_drawing_mode(raw) or looks_like_vector_path(text):
        return True
    if not text:
        return True
    alnum = re.findall(r"[^\W_]", text, flags=re.UNICODE)
    digits = re.findall(r"\d", text)
    if len(digits) >= 12 and len(digits) > len(alnum) * 2:
        return True
    return False


def convert(input_ass, output_srt):
    cues = []
    seen = set()
    for line in input_ass.read_text(encoding="utf-8-sig").splitlines():
        fields = parse_dialogue(line)
        if not fields:
            continue
        _layer, start, end, style, _name, _ml, _mr, _mv, effect, raw = fields
        text = strip_ass_text(raw)
        if is_skippable(style, effect, raw, text):
            continue
        start_ms = ass_time_to_ms(start)
        end_ms = ass_time_to_ms(end)
        if end_ms <= start_ms:
            continue
        key = (start_ms, end_ms, text)
        if key in seen:
            continue
        seen.add(key)
        cues.append(key)

    cues.sort(key=lambda item: (item[0], item[1], item[2]))

    output = []
    for index, (start_ms, end_ms, text) in enumerate(cues, start=1):
        output.extend(
            [
                str(index),
                f"{ms_to_srt_time(start_ms)} --> {ms_to_srt_time(end_ms)}",
                text,
                "",
            ]
        )
    output_srt.write_text("\n".join(output), encoding="utf-8-sig")
    return len(cues)


def main():
    parser = argparse.ArgumentParser(description="Convert ASS to a TV-safe SRT without ASS effects or drawing paths.")
    parser.add_argument("--input-ass", required=True)
    parser.add_argument("--output-srt", required=True)
    args = parser.parse_args()

    input_ass = Path(args.input_ass)
    output_srt = Path(args.output_srt)
    output_srt.parent.mkdir(parents=True, exist_ok=True)
    cue_count = convert(input_ass, output_srt)
    print(f"written cues: {cue_count}")
    print(f"written: {output_srt}")


if __name__ == "__main__":
    main()
