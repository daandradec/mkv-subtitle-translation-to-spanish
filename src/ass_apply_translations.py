#!/usr/bin/env python3
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from translation_terms import apply_terms, load_term_maps


DIALOGUE_PREFIX = "Dialogue: "


def parse_dialogue(line):
    if not line.startswith(DIALOGUE_PREFIX):
        return None
    fields = line[len(DIALOGUE_PREFIX) :].split(",", 9)
    if len(fields) != 10:
        return None
    return fields


def visible_text(raw):
    text = re.sub(r"\{[^{}]*\}", "", raw)
    return text.replace(r"\N", " ").replace(r"\n", " ").strip()


def leading_tags(raw):
    tags = []
    rest = raw
    while rest.startswith("{"):
        end = rest.find("}")
        if end < 0:
            break
        tags.append(rest[: end + 1])
        rest = rest[end + 1 :]
    return "".join(tags)


def replace_text_preserving_leading_tags(raw, translated):
    return leading_tags(raw) + translated


def load_json_maps(paths):
    event_map = {}
    song_map = {}
    for path in paths:
        p = Path(path)
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8-sig"))
        for key, value in data.items():
            if value is None:
                continue
            value = str(value).strip()
            if not value:
                continue
            if key.isdigit():
                event_map[int(key)] = value
            elif "|" in key:
                song_map[key] = value
    return event_map, song_map


def extract_pos_x(raw):
    match = re.search(r"\\pos\(([-0-9.]+),", raw)
    if not match:
        return 0.0
    return float(match.group(1))


def reconstruct_song_groups(lines):
    groups = defaultdict(list)
    for line in lines:
        fields = parse_dialogue(line)
        if not fields:
            continue
        layer, start, end, style, _name, _ml, _mr, _mv, effect, raw = fields
        if "English" not in style or effect != "fx" or layer != "2":
            continue
        text = re.sub(r"\{[^{}]*\}", "", raw)
        groups[f"{style}|{start}|{end}"].append((extract_pos_x(raw), text or " "))

    rebuilt = {}
    for key, chars in groups.items():
        text = "".join(ch for _x, ch in sorted(chars, key=lambda item: item[0]))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            rebuilt[key] = text
    return rebuilt


def is_song_english_style(style):
    return "English" in style


def main():
    parser = argparse.ArgumentParser(
        description="Apply Spanish translations to an ASS subtitle file without changing timings."
    )
    parser.add_argument("--input-ass", required=True)
    parser.add_argument("--output-ass", required=True)
    parser.add_argument("--translations", nargs="+", required=True)
    parser.add_argument(
        "--blank-translated-english-fx",
        action="store_true",
        help="Blank original per-letter English FX song lines when a Spanish song translation is present.",
    )
    parser.add_argument(
        "--term-map",
        nargs="*",
        default=[],
        help="Optional JSON glossary maps for normalizing names/terms after translation.",
    )
    args = parser.parse_args()

    input_path = Path(args.input_ass)
    output_path = Path(args.output_ass)
    lines = input_path.read_text(encoding="utf-8-sig").splitlines()
    event_map, song_map = load_json_maps(args.translations)
    term_map = load_term_maps(args.term_map)
    event_map = {key: apply_terms(value, term_map) for key, value in event_map.items()}
    song_map = {key: apply_terms(value, term_map) for key, value in song_map.items()}
    translated_song_keys = set(song_map)

    output = []
    in_events = False
    inserted_song_lines = False
    translated_events = 0
    blanked_fx_events = 0

    for line_no, line in enumerate(lines, start=1):
        if line.strip() == "[Events]":
            in_events = True
            output.append(line)
            continue

        fields = parse_dialogue(line)
        if in_events and fields:
            layer, start, end, style, name, ml, mr, mv, effect, raw = fields
            key = f"{style}|{start}|{end}"

            if line_no in event_map:
                fields[9] = replace_text_preserving_leading_tags(raw, event_map[line_no])
                output.append(DIALOGUE_PREFIX + ",".join(fields))
                translated_events += 1
                continue

            if (
                args.blank_translated_english_fx
                and is_song_english_style(style)
                and effect in ("fx", "karaoke")
            ):
                fields[9] = leading_tags(raw)
                output.append(DIALOGUE_PREFIX + ",".join(fields))
                blanked_fx_events += 1
                continue

        output.append(line)

    if song_map:
        output.append("")
        output.append("; Spanish song translations added by ass_apply_translations.py")
        for key in sorted(translated_song_keys, key=lambda item: item.split("|")[1]):
            style, start, end = key.split("|", 2)
            text = song_map[key]
            output.append(f"Dialogue: 99,{start},{end},{style},,0,0,30,,{text}")
            inserted_song_lines = True

    output_path.write_text("\n".join(output) + "\n", encoding="utf-8")

    original_dialogues = sum(1 for line in lines if line.startswith(DIALOGUE_PREFIX))
    final_dialogues = sum(1 for line in output if line.startswith(DIALOGUE_PREFIX))
    print(f"event translations applied: {translated_events}")
    print(f"song groups translated: {len(translated_song_keys)}")
    print(f"english fx events blanked: {blanked_fx_events}")
    print(f"original dialogue events: {original_dialogues}")
    print(f"final dialogue events: {final_dialogues}")
    print(f"inserted song lines: {inserted_song_lines}")
    print(f"written: {output_path}")


if __name__ == "__main__":
    main()
