#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter
from pathlib import Path

from video_generate_traslated_subtitles_from_existing_subtitles.ass_to_tv_safe_srt import (
    DIALOGUE_PREFIX,
    ass_time_to_ms,
    is_skippable,
    ms_to_srt_time,
    parse_dialogue,
    strip_ass_text,
)
from video_toolkit.temp_paths import managed_temporary_directory


WORD_REPLACEMENTS = [
    (r"\ba\?o\b", "año"),
    (r"\binvasi\?n\b", "invasión"),
    (r"\bpoblaci\?n\b", "población"),
    (r"\bsituaci\?n\b", "situación"),
    (r"\boperaci\?n\b", "operación"),
    (r"\bdecisi\?n\b", "decisión"),
    (r"\braz\?n\b", "razón"),
    (r"\bcoraz\?n\b", "corazón"),
    (r"\bdrag\?n\b", "dragón"),
    (r"\bavanz\?\b", "avanzó"),
    (r"\binici\?\b", "inició"),
    (r"\bsigui\?\b", "siguió"),
    (r"\bregres\?\b", "regresó"),
    (r"\bregres\?", "regresó"),
    (r"\bvolvi\?\b", "volvió"),
    (r"\brecibi\?\b", "recibió"),
    (r"\bempez\?\b", "empezó"),
    (r"\bpasar\?\b", "pasará"),
    (r"\bver\?n\b", "verán"),
    (r"\best\?", "está"),
    (r"\ba\?n\b", "aún"),
    (r"\bas\?\b", "así"),
    (r"\bAqu\?\b", "Aquí"),
    (r"\baqu\?\b", "aquí"),
    (r"\bS\?\b", "Sí"),
    (r"\bs\?\b", "sí"),
    (r"\bm\?s\b", "más"),
    (r"\bqu\?\b", "qué"),
    (r"\bQu\?\b", "Qué"),
    (r"\bc\?mo\b", "cómo"),
    (r"\bC\?mo\b", "Cómo"),
    (r"\bd\?nde\b", "dónde"),
    (r"\bD\?nde\b", "Dónde"),
    (r"\bcu\?nt", "cuánt"),
    (r"\bCu\?nt", "Cuánt"),
    (r"\bej\?rcito\b", "ejército"),
    (r"\br\?gimen\b", "régimen"),
    (r"\bt\?ctica\b", "táctica"),
    (r"\bl\?nea\b", "línea"),
    (r"\bre\?ne\b", "reúne"),
    (r"\bv\?veres\b", "víveres"),
    (r"\btambi\?n\b", "también"),
    (r"\bcacer\?a\b", "cacería"),
    (r"\btendr\?a\b", "tendría"),
    (r"\bser\?a\b", "sería"),
    (r"\bhabr\?a\b", "habría"),
    (r"\bpodr\?a\b", "podría"),
    (r"\bten\?a\b", "tenía"),
    (r"\bd\?a\b", "día"),
    (r"\br\?o\b", "río"),
    (r"\bJap\?n\b", "Japón"),
    (r"\bSeg\?n\b", "Según"),
    (r"\bseg\?n\b", "según"),
    (r"\besp\?as\b", "espías"),
    (r"\b\?xito\b", "éxito"),
    (r"\bDemasi\?ado\b", "Demasiado"),
    (r"\bdemasi\?ado\b", "demasiado"),
    (r"\bDemasíado\b", "Demasiado"),
    (r"\bdemasíado\b", "demasiado"),
    (r"\bocasíón\b", "ocasión"),
    (r"\bOcasíón\b", "Ocasión"),
    (r"\bRy\?mon\b", "Ryumon"),
    (r"\bpasi\?n\b", "pasión"),
    (r"\brecord\?\b", "recordó"),
    (r"\bpod\?a\b", "podía"),
    (r"\bm\?s\b", "más"),
    (r"\best\?n\b", "están"),
    (r"\bEstan\b", "Están"),
    (r"\bestan\b", "están"),
    (r"\btermin\?", "terminó"),
    (r"\?no\?", "¿no?"),
    (r"\?verdad\?", "¿verdad?"),
    (r"\bSe que\b", "Sé que"),
    (r"\bse que\b", "sé que"),
    (r"\blo se\b", "lo sé"),
    (r"\bLo se\b", "Lo sé"),
    (r"\bTu y yo\b", "Tú y yo"),
    (r"\btu y yo\b", "tú y yo"),
    (r"\bdia\b", "día"),
    (r"\bdias\b", "días"),
    (r"\bDia\b", "Día"),
    (r"\bDias\b", "Días"),
    (r"\bcorazon\b", "corazón"),
    (r"\bcorazones\b", "corazones"),
    (r"\bCorazon\b", "Corazón"),
    (r"\bsuenos\b", "sueños"),
    (r"\bSuenos\b", "Sueños"),
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
    (r"\bquiza\b", "quizá"),
    (r"\bQuiza\b", "Quizá"),
    (r"\bunico\b", "único"),
    (r"\bUnico\b", "Único"),
    (r"\bunica\b", "única"),
    (r"\bUnica\b", "Única"),
    (r"\bmelodia\b", "melodía"),
    (r"\bMelodia\b", "Melodía"),
    (r"\bmanana\b", "mañana"),
    (r"\bManana\b", "Mañana"),
    (r"\bsonreir\b", "sonreír"),
    (r"\boir\b", "oír"),
    (r"\bDejame\b", "Déjame"),
    (r"\bdejame\b", "déjame"),
    (r"\bEstare\b", "Estaré"),
    (r"\bestare\b", "estaré"),
    (r"\bquedare\b", "quedaré"),
    (r"\bseguira\b", "seguirá"),
    (r"\bSeguira\b", "Seguirá"),
    (r"\bseran\b", "serán"),
    (r"\bSeran\b", "Serán"),
    (r"\bseria\b", "sería"),
    (r"\bSeria\b", "Sería"),
    (r"\bharia\b", "haría"),
    (r"\bHaria\b", "Haría"),
    (r"\bdificil\b", "difícil"),
    (r"\bDificil\b", "Difícil"),
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
    (r"\bEsta justo\b", "Está justo"),
    (r"\bestas ahi\b", "estás ahí"),
    (r"\bSabias\?", "¿Sabías?"),
    (r"\bsabias\?", "¿sabías?"),
    (r"\bListos\?", "¿Listos?"),
    (r"\blistos\?", "¿listos?"),
    (r"\bsabes\?", "¿sabes?"),
    (r"\bOye, recuerdas cuando miramos el cielo\?", "Oye, ¿recuerdas cuando miramos el cielo?"),
    (r"\bQuizá todo sería más simple\?\?", "¿Quizá todo sería más simple?"),
    (r"\bNo te haría todo más difícil\?", "¿No te haría todo más difícil?"),
    (r", como serán mañana\?", ", ¿cómo serán mañana?"),
    (r"\bAún falta más!", "¡Aún falta más!"),
    (r"\bNo termino!", "¡No termino!"),
]


SPANISH_LETTERS = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
QUESTION_PREFIX_RE = r"(^|[\s\"'\(\[\{])"
SUSPICIOUS_QUESTION_RE = re.compile(
    rf"(?:(?<=[{SPANISH_LETTERS}])\?(?=[{SPANISH_LETTERS}])|{QUESTION_PREFIX_RE}\?(?=[{SPANISH_LETTERS}]))"
)


def normalize_spanish_text(text):
    normalized = text
    for pattern, replacement in WORD_REPLACEMENTS:
        normalized = re.sub(pattern, replacement, normalized)
    normalized = re.sub(r"(^|[\s\"'\(\[\{])\?([A-ZÁÉÍÓÚÜÑ][^?\n!]{0,80}!)", r"\1¡\2", normalized)
    normalized = re.sub(r"(^|[\s\"'\(\[\{])\?([A-ZÁÉÍÓÚÜÑ][^?\n]{0,80}\?)", r"\1¿\2", normalized)
    normalized = re.sub(r"\?no\?", "¿no?", normalized)
    normalized = re.sub(r"\?verdad\?", "¿verdad?", normalized)
    normalized = re.sub(r"¿{2,}", "¿", normalized)
    normalized = re.sub(r"¡{2,}", "¡", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    return normalized.strip()


def find_suspicious_question_marks(text):
    findings = []
    for match in SUSPICIOUS_QUESTION_RE.finditer(text):
        start = max(0, match.start() - 30)
        end = min(len(text), match.end() + 30)
        findings.append(
            {
                "offset": match.start(),
                "context": text[start:end].replace("\n", "\\n"),
            }
        )
    return findings


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


def comparable_visible_text(text):
    return re.sub(r"\s+", " ", text).strip()


def comparable_key(text):
    text = comparable_visible_text(text).casefold()
    text = re.sub(r"[^\wáéíóúüñ]+", " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def trim_repeated_suffix(previous_text, next_text):
    previous_flat = comparable_visible_text(previous_text)
    next_flat = comparable_visible_text(next_text)
    next_words = comparable_key(next_flat).split()
    if len(next_flat) < 18 and len(next_words) < 4:
        return previous_text, False
    if previous_flat == next_flat:
        return previous_text, False
    if not previous_flat.endswith(next_flat):
        return previous_text, False

    trimmed = previous_flat[: -len(next_flat)].rstrip(" ,;:-")
    if not trimmed:
        return previous_text, False
    if previous_flat[: -len(next_flat)].rstrip().endswith(":"):
        trimmed += "."
    return trimmed, True


def longest_suffix_prefix(left_words, right_words):
    max_size = min(len(left_words), len(right_words))
    for size in range(max_size, 0, -1):
        if left_words[-size:] == right_words[:size]:
            return size
    return 0


def longest_prefix_suffix(left_words, right_words):
    max_size = min(len(left_words), len(right_words))
    for size in range(max_size, 0, -1):
        if left_words[:size] == right_words[-size:]:
            return size
    return 0


def is_dense_short_cue(text, duration_ms):
    words = comparable_key(text).split()
    return duration_ms <= 1800 and len(words) >= 7


def is_adjacent_duplicate(current_text, previous_text, next_text, duration_ms):
    current_key = comparable_key(current_text)
    if not current_key:
        return False, ""
    if current_key == comparable_key(previous_text):
        return True, "duplicates_previous"
    if not is_dense_short_cue(current_text, duration_ms):
        return False, ""
    if current_key == comparable_key(next_text):
        return True, "duplicates_next"

    previous_words = comparable_key(previous_text).split()
    current_words = current_key.split()
    next_words = comparable_key(next_text).split()
    if len(current_words) < 7:
        return False, ""

    previous_overlap = longest_suffix_prefix(previous_words, current_words)
    next_overlap = longest_prefix_suffix(next_words, current_words)
    covered = previous_overlap + next_overlap
    has_meaningful_overlap = previous_overlap >= 2 and next_overlap >= 3
    mostly_covered = covered >= len(current_words) - 1
    if has_meaningful_overlap and mostly_covered:
        return True, "bridge_from_previous_and_next"
    return False, ""


def split_final_sentence(text):
    flat = comparable_visible_text(text)
    matches = list(re.finditer(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÜÑ¡¿])", flat))
    if not matches:
        return flat, ""
    split_at = matches[-1].end()
    head = flat[:split_at].strip()
    tail = flat[split_at:].strip()
    if not head or not tail:
        return flat, ""
    return head, tail


def redistribute_adjacent_prefix_overlaps(lines):
    output = list(lines)
    changes = []
    dialogue_indexes = []
    for index, line in enumerate(output):
        fields = parse_dialogue(line)
        if not fields:
            continue
        _layer, _start, _end, style, _name, _ml, _mr, _mv, effect, raw = fields
        visible = strip_ass_text(raw)
        if is_skippable(style, effect, raw, visible):
            continue
        dialogue_indexes.append(index)

    for left_index, right_index in zip(dialogue_indexes, dialogue_indexes[1:]):
        left_fields = parse_dialogue(output[left_index])
        right_fields = parse_dialogue(output[right_index])
        if not left_fields or not right_fields:
            continue

        left_text = comparable_visible_text(strip_ass_text(left_fields[9]))
        right_text = comparable_visible_text(strip_ass_text(right_fields[9]))
        if not left_text or not right_text:
            continue
        if comparable_key(left_text) == comparable_key(right_text):
            continue
        if not comparable_key(right_text).startswith(comparable_key(left_text)):
            continue

        # Prefer direct textual remainder when punctuation/casing has stayed stable.
        if right_text.startswith(left_text):
            remainder = right_text[len(left_text) :].strip(" ,;:-")
        else:
            right_words = right_text.split()
            left_word_count = len(left_text.split())
            remainder = " ".join(right_words[left_word_count:]).strip(" ,;:-")
        if not remainder:
            continue

        left_head, left_tail = split_final_sentence(left_text)
        if left_tail:
            new_left = left_head
            new_right = f"{left_tail} {remainder}".strip()
        else:
            new_left = left_text
            new_right = remainder

        left_tags, _left_rest = leading_tags(left_fields[9])
        right_tags, _right_rest = leading_tags(right_fields[9])
        left_fields[9] = left_tags + new_left
        right_fields[9] = right_tags + new_right
        output[left_index] = DIALOGUE_PREFIX + ",".join(left_fields)
        output[right_index] = DIALOGUE_PREFIX + ",".join(right_fields)
        changes.append(
            {
                "previous_line": left_index + 1,
                "current_line": right_index + 1,
                "previous_before": left_text,
                "current_before": right_text,
                "previous_after": new_left,
                "current_after": new_right,
            }
        )

    return output, changes


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


def remove_adjacent_duplicate_cues(lines):
    output = list(lines)
    removed = []
    dialogue_items = []
    for index, line in enumerate(output):
        fields = parse_dialogue(line)
        if not fields:
            continue
        _layer, start, end, style, _name, _ml, _mr, _mv, effect, raw = fields
        visible = strip_ass_text(raw)
        if is_skippable(style, effect, raw, visible):
            continue
        dialogue_items.append(
            {
                "index": index,
                "start_ms": ass_time_to_ms(start),
                "end_ms": ass_time_to_ms(end),
                "text": visible,
            }
        )

    indexes_to_remove = set()
    extension_by_index = {}
    for previous_item, current_item, next_item in zip(dialogue_items, dialogue_items[1:], dialogue_items[2:]):
        duration_ms = current_item["end_ms"] - current_item["start_ms"]
        should_remove, reason = is_adjacent_duplicate(
            current_item["text"],
            previous_item["text"],
            next_item["text"],
            duration_ms,
        )
        if not should_remove:
            continue
        indexes_to_remove.add(current_item["index"])
        extension_by_index[previous_item["index"]] = max(
            extension_by_index.get(previous_item["index"], previous_item["end_ms"]),
            current_item["end_ms"],
        )
        removed.append(
            {
                "line": current_item["index"] + 1,
                "reason": reason,
                "duration_ms": duration_ms,
                "previous_line": previous_item["index"] + 1,
                "previous_end_before_ms": previous_item["end_ms"],
                "previous_end_after_ms": current_item["end_ms"],
                "text": comparable_visible_text(current_item["text"]),
                "previous": comparable_visible_text(previous_item["text"]),
                "next": comparable_visible_text(next_item["text"]),
            }
        )

    for index, extended_end_ms in extension_by_index.items():
        fields = parse_dialogue(output[index])
        if not fields:
            continue
        fields[2] = ms_to_ass_time(extended_end_ms)
        output[index] = DIALOGUE_PREFIX + ",".join(fields)

    return [line for index, line in enumerate(output) if index not in indexes_to_remove], removed


def trim_adjacent_repeated_fragments(lines):
    output = list(lines)
    changed = []
    dialogue_indexes = []
    for index, line in enumerate(output):
        fields = parse_dialogue(line)
        if not fields:
            continue
        _layer, _start, _end, style, _name, _ml, _mr, _mv, effect, raw = fields
        visible = strip_ass_text(raw)
        if is_skippable(style, effect, raw, visible):
            continue
        dialogue_indexes.append(index)

    for left_index, right_index in zip(dialogue_indexes, dialogue_indexes[1:]):
        left_fields = parse_dialogue(output[left_index])
        right_fields = parse_dialogue(output[right_index])
        if not left_fields or not right_fields:
            continue

        left_text = strip_ass_text(left_fields[9])
        right_text = strip_ass_text(right_fields[9])
        trimmed_text, did_trim = trim_repeated_suffix(left_text, right_text)
        if not did_trim:
            continue

        tags, _rest = leading_tags(left_fields[9])
        left_fields[9] = tags + trimmed_text
        output[left_index] = DIALOGUE_PREFIX + ",".join(left_fields)
        changed.append(
            {
                "line": left_index + 1,
                "removed_before_next_line": right_index + 1,
                "before": comparable_visible_text(left_text),
                "after": trimmed_text,
                "next": comparable_visible_text(right_text),
            }
        )

    return output, changed


def cue_counter(cues):
    return Counter((cue["start_ms"], cue["end_ms"], normalize_spanish_text(cue["text"])) for cue in cues)


def normalize_files(input_ass, input_srt, output_ass, output_srt, report_path, reported_output_ass=None, reported_output_srt=None):
    original_ass_lines = input_ass.read_text(encoding="utf-8-sig").splitlines()
    original_srt_cues = parse_srt(input_srt) if input_srt.exists() else []

    normalized_ass_lines, ass_stats = normalize_ass_lines(original_ass_lines)
    normalized_ass_lines, prefix_overlap_changes = redistribute_adjacent_prefix_overlaps(normalized_ass_lines)
    normalized_ass_lines, adjacent_duplicate_removals = remove_adjacent_duplicate_cues(normalized_ass_lines)
    normalized_ass_lines, repeated_fragment_changes = trim_adjacent_repeated_fragments(normalized_ass_lines)
    normalized_cues = build_tv_safe_cues_from_ass(normalized_ass_lines)

    output_ass.parent.mkdir(parents=True, exist_ok=True)
    output_srt.parent.mkdir(parents=True, exist_ok=True)
    output_ass.write_text("\n".join(normalized_ass_lines) + "\n", encoding="utf-8")
    write_srt(normalized_cues, output_srt)

    generated_counter = Counter(normalized_cues)
    input_counter = cue_counter(original_srt_cues)
    changed_srt_groups = sum((generated_counter - input_counter).values())
    suspicious = []
    for line_no, line in enumerate(normalized_ass_lines, start=1):
        fields = parse_dialogue(line)
        if not fields:
            continue
        text = strip_ass_text(fields[9])
        for finding in find_suspicious_question_marks(text):
            suspicious.append({"file": "ass", "line": line_no, **finding})
    for cue_index, (_start_ms, _end_ms, text) in enumerate(normalized_cues, start=1):
        for finding in find_suspicious_question_marks(text):
            suspicious.append({"file": "srt", "cue": cue_index, **finding})

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
        "quality": {
            "suspicious_question_replacements": suspicious,
            "suspicious_question_replacement_count": len(suspicious),
            "adjacent_prefix_overlaps_redistributed": prefix_overlap_changes,
            "adjacent_prefix_overlap_redistribution_count": len(prefix_overlap_changes),
            "adjacent_duplicate_cues_removed": adjacent_duplicate_removals,
            "adjacent_duplicate_cue_removal_count": len(adjacent_duplicate_removals),
            "adjacent_repeated_fragments_trimmed": repeated_fragment_changes,
            "adjacent_repeated_fragment_trim_count": len(repeated_fragment_changes),
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

    with managed_temporary_directory(prefix="subtitle_normalize_") as temp_dir:
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
    print(f"adjacent prefix overlaps redistributed: {report['quality']['adjacent_prefix_overlap_redistribution_count']}")
    print(f"adjacent duplicate cues removed: {report['quality']['adjacent_duplicate_cue_removal_count']}")
    print(f"adjacent repeated fragments trimmed: {report['quality']['adjacent_repeated_fragment_trim_count']}")
    print(f"srt input cues: {report['srt']['input_cues']}")
    print(f"srt output cues: {report['srt']['output_cues']}")
    print(f"written: {output_ass}")
    print(f"written: {output_srt}")
    print(f"report: {report_path}")
    if report["quality"]["suspicious_question_replacement_count"]:
        raise SystemExit(
            "Spanish subtitle quality validation failed: suspicious '?' replacements remain. "
            f"See report: {report_path}"
        )


if __name__ == "__main__":
    main()
