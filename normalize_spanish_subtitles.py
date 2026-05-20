#!/usr/bin/env python3
import argparse
import json
import re
import tempfile
from collections import Counter
from pathlib import Path

from ass_to_tv_safe_srt import (
    DIALOGUE_PREFIX,
    ass_time_to_ms,
    is_skippable,
    ms_to_srt_time,
    parse_dialogue,
    strip_ass_text,
)


WORD_REPLACEMENTS = [
    (r"\bpasi\?n\b", "pasión"),
    (r"\brecord\?\b", "recordó"),
    (r"\bpod\?a\b", "podía"),
    (r"\bm\?s\b", "más"),
    (r"\best\?n\b", "están"),
    (r"\?no\?", "¿no?"),
    (r"\bSe que\b", "Sé que"),
    (r"\bse que\b", "sé que"),
    (r"\bTu y yo\b", "Tú y yo"),
    (r"\btu y yo\b", "tú y yo"),
    (r"\bdia\b", "día"),
    (r"\bdias\b", "días"),
    (r"\bDia\b", "Día"),
    (r"\bDias\b", "Días"),
    (r"\bcorazon\b", "corazón"),
    (r"\bcorazones\b", "corazones"),
    (r"\bCorazon\b", "Corazón"),
    (r"\bcancion\b", "canción"),
    (r"\bcanciones\b", "canciones"),
    (r"\bemocion\b", "emoción"),
    (r"\bemociones\b", "emociones"),
    (r"\bpasion\b", "pasión"),
    (r"\btambien\b", "también"),
    (r"\bTambien\b", "También"),
    (r"\bdespues\b", "después"),
    (r"\bDespues\b", "Después"),
    (r"\bademas\b", "además"),
    (r"\bAdemas\b", "Además"),
    (r"\basi\b", "así"),
    (r"\bAsi\b", "Así"),
    (r"\baqui\b", "aquí"),
    (r"\bAqui\b", "Aquí"),
    (r"\balli\b", "allí"),
    (r"\bAlli\b", "Allí"),
    (r"\bahi\b", "ahí"),
    (r"\bAhi\b", "Ahí"),
    (r"\bmas\b", "más"),
    (r"\bMas\b", "Más"),
    (r"\baun\b", "aún"),
    (r"\bAun\b", "Aún"),
    (r"\btodavia\b", "todavía"),
    (r"\bTodavia\b", "Todavía"),
    (r"\bunico\b", "único"),
    (r"\bUnico\b", "Único"),
    (r"\bunica\b", "única"),
    (r"\bUnica\b", "Única"),
    (r"\bmelodia\b", "melodía"),
    (r"\bMelodia\b", "Melodía"),
    (r"\bsonreir\b", "sonreír"),
    (r"\boir\b", "oír"),
    (r"\bDejame\b", "Déjame"),
    (r"\bdejame\b", "déjame"),
    (r"\bEstare\b", "Estaré"),
    (r"\bestare\b", "estaré"),
    (r"\bquedare\b", "quedaré"),
    (r"\bseguira\b", "seguirá"),
    (r"\bSeguira\b", "Seguirá"),
    (r"\bempezo\b", "empezó"),
    (r"\bEmpezo\b", "Empezó"),
    (r"\baparto\b", "apartó"),
    (r"\bqueria\b", "quería"),
    (r"\bfingi\b", "fingí"),
    (r"\bTropece\b", "Tropecé"),
    (r"\btropece\b", "tropecé"),
    (r"\bluche\b", "luché"),
    (r"\blastime\b", "lastimé"),
    (r"\besta fuera\b", "está fuera"),
    (r"\bEsta fuera\b", "Está fuera"),
    (r"\besta bien\b", "está bien"),
    (r"\bEsta bien\b", "Está bien"),
    (r"\bestas ahi\b", "estás ahí"),
]


def normalize_spanish_text(text):
    normalized = text
    for pattern, replacement in WORD_REPLACEMENTS:
        normalized = re.sub(pattern, replacement, normalized)
    if normalized.startswith("?") and normalized.endswith("!"):
        normalized = "¡" + normalized[1:]
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    return normalized.strip()


def leading_tags(raw):
    tags = []
    rest = raw
    while rest.startswith("{"):
        end = rest.find("}")
        if end < 0:
            break
        tags.append(rest[: end + 1])
        rest = rest[end + 1 :]
    return "".join(tags), rest


def normalize_ass_raw_text(raw):
    tags, rest = leading_tags(raw)
    if "{" in rest or "}" in rest:
        return raw, False
    normalized_rest = normalize_spanish_text(rest)
    if normalized_rest == rest.strip():
        return raw, False
    return tags + normalized_rest, True


def parse_srt_timestamp(value):
    hours, minutes, rest = value.split(":")
    seconds, milliseconds = rest.split(",")
    return (
        int(hours) * 3_600_000
        + int(minutes) * 60_000
        + int(seconds) * 1_000
        + int(milliseconds)
    )


def parse_srt(path):
    text = path.read_text(encoding="utf-8-sig")
    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [line.rstrip("\r") for line in block.splitlines() if line.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start_raw, end_raw = [part.strip() for part in lines[1].split("-->", 1)]
        cues.append(
            {
                "start_ms": parse_srt_timestamp(start_raw),
                "end_ms": parse_srt_timestamp(end_raw),
                "text": "\n".join(lines[2:]).strip(),
            }
        )
    return cues


def build_tv_safe_cues_from_ass(lines):
    cues = []
    seen = set()
    for line in lines:
        fields = parse_dialogue(line)
        if not fields:
            continue
        _layer, start, end, style, _name, _ml, _mr, _mv, effect, raw = fields
        text = normalize_spanish_text(strip_ass_text(raw))
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
    return sorted(cues, key=lambda item: (item[0], item[1], item[2]))


def write_srt(cues, output_path):
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
    output_path.write_text("\n".join(output), encoding="utf-8-sig")


def normalize_ass_lines(lines):
    output = []
    changed_lines = 0
    visible_events = 0
    skipped_events = 0
    for line in lines:
        fields = parse_dialogue(line)
        if not fields:
            output.append(line)
            continue

        _layer, _start, _end, style, _name, _ml, _mr, _mv, effect, raw = fields
        visible = strip_ass_text(raw)
        if is_skippable(style, effect, raw, visible):
            skipped_events += 1
            output.append(line)
            continue

        visible_events += 1
        normalized_raw, changed = normalize_ass_raw_text(raw)
        if changed:
            fields[9] = normalized_raw
            line = DIALOGUE_PREFIX + ",".join(fields)
            changed_lines += 1
        output.append(line)
    return output, {"changed_lines": changed_lines, "visible_events": visible_events, "skipped_events": skipped_events}


def cue_counter(cues):
    return Counter((cue["start_ms"], cue["end_ms"], normalize_spanish_text(cue["text"])) for cue in cues)


def normalize_files(input_ass, input_srt, output_ass, output_srt, report_path, reported_output_ass=None, reported_output_srt=None):
    original_ass_lines = input_ass.read_text(encoding="utf-8-sig").splitlines()
    original_srt_cues = parse_srt(input_srt) if input_srt.exists() else []

    normalized_ass_lines, ass_stats = normalize_ass_lines(original_ass_lines)
    normalized_cues = build_tv_safe_cues_from_ass(normalized_ass_lines)

    output_ass.parent.mkdir(parents=True, exist_ok=True)
    output_srt.parent.mkdir(parents=True, exist_ok=True)
    output_ass.write_text("\n".join(normalized_ass_lines) + "\n", encoding="utf-8")
    write_srt(normalized_cues, output_srt)

    generated_counter = Counter(normalized_cues)
    input_counter = cue_counter(original_srt_cues)
    changed_srt_groups = sum((generated_counter - input_counter).values())

    report = {
        "input_ass": str(input_ass),
        "input_srt": str(input_srt),
        "output_ass": str(reported_output_ass or output_ass),
        "output_srt": str(reported_output_srt or output_srt),
        "ass": ass_stats,
        "srt": {
            "input_cues": len(original_srt_cues),
            "output_cues": len(normalized_cues),
            "changed_or_added_groups": changed_srt_groups,
        },
        "policy": {
            "text_base": "ASS visible text",
            "preserve_overlaps": True,
            "preserve_timings": True,
            "tv_safe_filters": [
                "ASS override tags",
                "drawing paths",
                "romaji/kanji effect events",
                "placeholders",
                "numeric garbage",
            ],
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def replace_path(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.replace(destination)


def main():
    parser = argparse.ArgumentParser(
        description="Normalize generated Spanish ASS and TV-safe SRT subtitles after the initial MKV workflow."
    )
    parser.add_argument("--input-ass", required=True)
    parser.add_argument("--input-srt", required=True)
    parser.add_argument("--output-ass", required=True)
    parser.add_argument("--output-srt", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    input_ass = Path(args.input_ass)
    input_srt = Path(args.input_srt)
    output_ass = Path(args.output_ass)
    output_srt = Path(args.output_srt)
    report_path = Path(args.report)

    with tempfile.TemporaryDirectory(prefix="subtitle_normalize_") as temp_dir:
        temp = Path(temp_dir)
        temp_ass = temp / "normalized.ass"
        temp_srt = temp / "normalized.srt"
        temp_report = temp / "report.json"
        report = normalize_files(
            input_ass,
            input_srt,
            temp_ass,
            temp_srt,
            temp_report,
            reported_output_ass=output_ass,
            reported_output_srt=output_srt,
        )
        replace_path(temp_ass, output_ass)
        replace_path(temp_srt, output_srt)
        replace_path(temp_report, report_path)

    print(f"ass visible events: {report['ass']['visible_events']}")
    print(f"ass lines normalized: {report['ass']['changed_lines']}")
    print(f"srt input cues: {report['srt']['input_cues']}")
    print(f"srt output cues: {report['srt']['output_cues']}")
    print(f"written: {output_ass}")
    print(f"written: {output_srt}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
