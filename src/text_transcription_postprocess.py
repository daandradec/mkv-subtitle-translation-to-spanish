#!/usr/bin/env python3
import argparse
import base64
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

from subtitle_text_to_ass import parse_text_subtitles
from transcription_postprocess import find_backend_output, read_detected_language


BOILERPLATE_PATTERNS = [
    r"^\s*subt[i\u00ed]tulos?\s+(realizados|creados|hechos)\s+por\b.*$",
    r"^\s*subtitles?\s+(by|created by|made by)\b.*$",
    r"^\s*caption[s]?\s+(by|created by)\b.*$",
    r"^\s*transcripci[o\u00f3]n\s+(realizada|generada)\s+por\b.*$",
    r"^\s*(gracias|thank you|merci|obrigado|obrigada)\s+(por\s+ver|for watching|d'avoir regard[e\u00e9]|por assistir)\.?\s*$",
    r"^\s*(suscr[i\u00ed]bete|subscribe|like\s+and\s+subscribe|dale\s+like)\b.*$",
]

NOISE_PATTERNS = [
    r"^\s*\[(music|m[u\u00fa]sica|applause|aplausos|laughter|risas|silence|silencio|noise|ruido)\]\s*$",
    r"^\s*\((music|m[u\u00fa]sica|applause|aplausos|laughter|risas|silence|silencio|noise|ruido)\)\s*$",
]

FILLERS = {
    "es": {"eh", "em", "mmm", "aj\u00e1", "este", "bueno", "o sea", "digamos"},
    "en": {"uh", "um", "mmm", "you know", "like", "well"},
    "fr": {"euh", "hum", "ben", "bah"},
    "pt": {"\u00e9", "hum", "ahn", "tipo"},
    "de": {"\u00e4h", "\u00e4hm", "hm"},
    "it": {"eh", "ehm", "cio\u00e8"},
    "ja": {"\u3048\u30fc", "\u3042\u306e", "\u305d\u306e"},
    "ko": {"\uc74c", "\uc5b4", "\uadf8"},
    "zh": {"\u55ef", "\u5443", "\u90a3\u4e2a"},
}

SPANISH_REPLACEMENTS = {
    "?Que": "\u00bfQu\u00e9",
    "?Qu\u00e9": "\u00bfQu\u00e9",
    "?Como": "\u00bfC\u00f3mo",
    "?C\u00f3mo": "\u00bfC\u00f3mo",
    "?Cuando": "\u00bfCu\u00e1ndo",
    "?Cu\u00e1ndo": "\u00bfCu\u00e1ndo",
    "?Donde": "\u00bfD\u00f3nde",
    "?D\u00f3nde": "\u00bfD\u00f3nde",
    "?Por que": "\u00bfPor qu\u00e9",
    "?Por qu\u00e9": "\u00bfPor qu\u00e9",
    "?Es": "\u00bfEs",
    "?No": "\u00bfNo",
    "?Si": "\u00bfS\u00ed",
    "?Sera": "\u00bfSer\u00e1",
    "?Ser\u00e1": "\u00bfSer\u00e1",
    "?Puede": "\u00bfPuede",
}

SPANISH_SEMANTIC_RULES = [
    (re.compile(r"\b(se\u00f1or|se\u00f1ora)\s+de\s+Lugar\b", re.IGNORECASE), r"\1 del lugar"),
    (re.compile(r"\b(se\u00f1or|se\u00f1ora)\s+Lugar\b", re.IGNORECASE), r"\1 del lugar"),
    (re.compile(r"\bperd[i\u00ed]\s+permiso\b", re.IGNORECASE), "ped\u00ed permiso"),
    (re.compile(r"\bpunto,\s+pero\b", re.IGNORECASE), "punto. Pero"),
]

MOJIBAKE_REPLACEMENTS = {
    "\u00c3\u00a1": "\u00e1",
    "\u00c3\u00a9": "\u00e9",
    "\u00c3\u00ad": "\u00ed",
    "\u00c3\u00b3": "\u00f3",
    "\u00c3\u00ba": "\u00fa",
    "\u00c3\u0081": "\u00c1",
    "\u00c3\u0089": "\u00c9",
    "\u00c3\u008d": "\u00cd",
    "\u00c3\u0093": "\u00d3",
    "\u00c3\u009a": "\u00da",
    "\u00c3\u00b1": "\u00f1",
    "\u00c3\u0091": "\u00d1",
    "\u00c3\u00bc": "\u00fc",
    "\u00c3\u009c": "\u00dc",
    "\u00c2\u00bf": "\u00bf",
    "\u00c2\u00a1": "\u00a1",
    "\u00c2\u00ab": "\u00ab",
    "\u00c2\u00bb": "\u00bb",
    "\u00c2\u00b0": "\u00b0",
    "\u00c2\u00b4": "\u00b4",
    "\u00c2": "",
}

SENTENCE_END_RE = re.compile(r"[.!?\u3002\uff01\uff1f]\s*$")
WORD_RE = re.compile(r"\w+", re.UNICODE)
MOJIBAKE_MARKERS = ("\u00c3", "\u00c2", "\ufffd")


@dataclass
class Segment:
    start: float
    end: float
    text: str


def decode_json_argument(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        decoded = base64.b64decode(value, validate=True).decode("utf-8")
        return json.loads(decoded)


def normalize_space(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def normalize_encoding_artifacts(text, language="", repair_language_punctuation=True):
    text = text.replace("\ufeff", "").replace("\u200b", "")
    text = text.replace("\ufffd", "")
    for bad, good in MOJIBAKE_REPLACEMENTS.items():
        text = text.replace(bad, good)
    if repair_language_punctuation and (language or "").lower().startswith("es"):
        for bad, good in SPANISH_REPLACEMENTS.items():
            text = text.replace(bad, good)
        text = re.sub(
            r"(^|\s)\?([A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1])",
            lambda match: f"{match.group(1)}\u00bf{match.group(2)}",
            text,
        )
    return text


def normalize_semantics(text, language=""):
    if not (language or "").lower().startswith("es"):
        return text
    for pattern, replacement in SPANISH_SEMANTIC_RULES:
        text = pattern.sub(replacement, text)
    return text


def remove_repeated_words(text):
    words = text.split()
    if len(words) < 2:
        return text
    cleaned = []
    for word in words:
        normalized = re.sub(r"\W+", "", word).casefold()
        previous = re.sub(r"\W+", "", cleaned[-1]).casefold() if cleaned else ""
        if normalized and normalized == previous:
            continue
        cleaned.append(word)
    return " ".join(cleaned)


def collapse_repeated_phrases(text):
    text = normalize_space(text)
    parts = re.split(r"([,.;:!?\u3002\uff01\uff1f])", text)
    if len(parts) <= 1:
        return text
    rebuilt = []
    previous_norm = ""
    for index in range(0, len(parts), 2):
        phrase = normalize_space(parts[index])
        punctuation = parts[index + 1] if index + 1 < len(parts) else ""
        norm = re.sub(r"\W+", "", phrase).casefold()
        if norm and norm == previous_norm:
            continue
        if phrase:
            rebuilt.append(f"{phrase}{punctuation}")
            previous_norm = norm
    return normalize_space(" ".join(rebuilt))


def is_noise_or_boilerplate(text):
    value = normalize_space(text)
    if not value:
        return True
    for pattern in NOISE_PATTERNS + BOILERPLATE_PATTERNS:
        if re.match(pattern, value, flags=re.IGNORECASE):
            return True
    alnum_count = sum(1 for char in value if char.isalnum())
    return alnum_count == 0


def is_filler_only(text, language=""):
    value = normalize_space(text).casefold().strip(".,;:!?\u00a1\u00bf()[] ")
    if not value:
        return True
    fillers = set(FILLERS.get((language or "").lower(), set()))
    fillers.update(FILLERS.get((language or "").lower().split("-")[0], set()))
    generic = {"uh", "um", "mmm", "hmm", "eh", "em"}
    fillers.update(generic)
    return value in fillers


def clean_segment_text(text, language="", verbatim=False):
    text = normalize_encoding_artifacts(
        text,
        language=language,
        repair_language_punctuation=not verbatim,
    )
    if verbatim:
        return normalize_space(text)
    text = normalize_semantics(text, language=language)
    text = normalize_space(text)
    if is_noise_or_boilerplate(text) or is_filler_only(text, language=language):
        return ""
    text = remove_repeated_words(text)
    text = collapse_repeated_phrases(text)
    return normalize_space(text)


def read_json_segments(json_path):
    if not json_path or not Path(json_path).exists():
        return [], ""
    data = json.loads(Path(json_path).read_text(encoding="utf-8-sig"))
    language = str(data.get("language") or "").strip()
    segments = []
    for item in data.get("segments", []):
        text = normalize_space(str(item.get("text") or ""))
        if not text:
            continue
        start = float(item.get("start") or 0)
        end = float(item.get("end") or start)
        if end <= start:
            end = start + 0.01
        segments.append(Segment(start=start, end=end, text=text))
    return segments, language


def read_srt_or_vtt_segments(path, fmt):
    if not path or not Path(path).exists():
        return []
    cues = parse_text_subtitles(Path(path), fmt)
    return [Segment(start=cue.start_ms / 1000, end=cue.end_ms / 1000, text=cue.text) for cue in cues]


def read_txt_segments(path):
    if not path or not Path(path).exists():
        return []
    text = normalize_space(Path(path).read_text(encoding="utf-8-sig"))
    return [Segment(start=0, end=0, text=text)] if text else []


def load_segments(output_dir, audio_stem, requested_language=""):
    raw_json = find_backend_output(output_dir, audio_stem, ".json")
    segments, language = read_json_segments(raw_json)
    if not segments:
        srt = find_backend_output(output_dir, audio_stem, ".srt")
        segments = read_srt_or_vtt_segments(srt, "srt")
    if not segments:
        vtt = find_backend_output(output_dir, audio_stem, ".vtt")
        segments = read_srt_or_vtt_segments(vtt, "vtt")
    if not segments:
        txt = find_backend_output(output_dir, audio_stem, ".txt")
        segments = read_txt_segments(txt)
    detected_language = requested_language or language
    return segments, detected_language, raw_json


def infer_language_from_text(segments, detected_language):
    key = (detected_language or "").lower()
    if key and key not in {"en", "eng", "english", "und", "unknown"}:
        return detected_language
    sample = " ".join(normalize_encoding_artifacts(segment.text, "es") for segment in segments[:20]).casefold()
    spanish_markers = [
        "\u00bf",
        "\u00a1",
        " qu\u00e9 ",
        " que ",
        " s\u00ed ",
        " se\u00f1or",
        " se\u00f1ora",
        " por ",
        " para ",
        " cierto",
        " grabaci\u00f3n",
        " estoy ",
        " est\u00e1 ",
        " est\u00e1n ",
        " profe",
        " sesi\u00f3n",
        " ma\u00f1ana",
        " tiempo",
    ]
    score = sum(1 for marker in spanish_markers if marker in sample)
    return "es" if score >= 4 else detected_language


def canonicalize_native_outputs(output_dir, audio_stem, video_stem):
    output_dir = Path(output_dir)
    copied = {}
    for suffix in [".json", ".srt", ".vtt", ".txt", ".tsv"]:
        source = find_backend_output(output_dir, audio_stem, suffix)
        target = output_dir / f"{video_stem}{suffix}"
        if source and source.exists():
            if source.resolve() != target.resolve():
                shutil.copy2(source, target)
            copied[suffix.lstrip(".")] = str(target)
    return copied


def seconds_to_srt_time(value):
    milliseconds_value = max(0, int(round(value * 1000)))
    hours, remainder = divmod(milliseconds_value, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def seconds_to_vtt_time(value):
    return seconds_to_srt_time(value).replace(",", ".")


def write_clean_srt(segments, output_path):
    blocks = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{seconds_to_srt_time(segment.start)} --> {seconds_to_srt_time(segment.end)}",
                    segment.text,
                ]
            )
        )
    Path(output_path).write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def write_clean_vtt(segments, output_path):
    blocks = ["WEBVTT", ""]
    for segment in segments:
        blocks.append(f"{seconds_to_vtt_time(segment.start)} --> {seconds_to_vtt_time(segment.end)}")
        blocks.append(segment.text)
        blocks.append("")
    Path(output_path).write_text("\n".join(blocks).rstrip() + "\n", encoding="utf-8")


def write_clean_txt(segments, output_path):
    paragraphs = [segment.text for segment in segments if segment.text]
    Path(output_path).write_text("\n".join(paragraphs).rstrip() + "\n", encoding="utf-8")


def write_clean_text_outputs(cleaned_segments, output_dir, video_stem):
    output_dir = Path(output_dir)
    outputs = {
        "srt": output_dir / f"{video_stem}.srt",
        "vtt": output_dir / f"{video_stem}.vtt",
        "txt": output_dir / f"{video_stem}.txt",
    }
    write_clean_srt(cleaned_segments, outputs["srt"])
    write_clean_vtt(cleaned_segments, outputs["vtt"])
    write_clean_txt(cleaned_segments, outputs["txt"])
    return {key: str(path) for key, path in outputs.items()}


def clean_segments(segments, language="", verbatim=False):
    cleaned = []
    previous_norm = ""
    removed = 0
    for segment in segments:
        text = clean_segment_text(segment.text, language=language, verbatim=verbatim)
        norm = re.sub(r"\W+", "", text).casefold()
        if not text:
            removed += 1
            continue
        if not verbatim and norm and norm == previous_norm:
            removed += 1
            continue
        cleaned.append(Segment(start=segment.start, end=segment.end, text=text))
        previous_norm = norm
    return cleaned, removed


def format_time(seconds):
    seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{secs:02}"


def should_start_new_paragraph(current_texts, segment, previous_segment, max_chars):
    if not current_texts:
        return False
    current_chars = sum(len(item) for item in current_texts)
    if current_chars >= max_chars:
        return True
    if previous_segment and segment.start - previous_segment.end >= 2.5:
        return True
    return bool(previous_segment and SENTENCE_END_RE.search(previous_segment.text) and current_chars >= max_chars * 0.45)


def build_markdown_sections(segments, section_seconds=180, paragraph_max_chars=900):
    if not segments:
        return []
    sections = []
    section_start = segments[0].start
    section_end = section_start + section_seconds
    section_segments = []

    def flush_section(items):
        if not items:
            return
        paragraphs = []
        current = []
        previous = None
        for segment in items:
            if should_start_new_paragraph(current, segment, previous, paragraph_max_chars):
                paragraphs.append(normalize_space(" ".join(current)))
                current = []
            current.append(segment.text)
            previous = segment
        if current:
            paragraphs.append(normalize_space(" ".join(current)))
        sections.append(
            {
                "start": items[0].start,
                "end": items[-1].end,
                "paragraphs": [paragraph for paragraph in paragraphs if paragraph],
            }
        )

    for segment in segments:
        if segment.start >= section_end and section_segments:
            flush_section(section_segments)
            section_segments = []
            section_start = segment.start
            section_end = section_start + section_seconds
        section_segments.append(segment)
    flush_section(section_segments)
    return sections


def normalize_for_alignment(text, language="", verbatim=False):
    text = clean_segment_text(text, language=language, verbatim=verbatim)
    text = text.casefold()
    return re.sub(r"[^0-9a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00fc\u00f1]+", "", text)


def build_markdown_paragraphs(segments, paragraph_max_chars=900):
    paragraphs = []
    current_texts = []
    current_segments = []
    previous = None

    def flush():
        if not current_texts or not current_segments:
            return
        paragraphs.append(
            {
                "start": current_segments[0].start,
                "end": current_segments[-1].end,
                "text": normalize_space(" ".join(current_texts)),
            }
        )

    for segment in segments:
        if should_start_new_paragraph(current_texts, segment, previous, paragraph_max_chars):
            flush()
            current_texts = []
            current_segments = []
        current_texts.append(segment.text)
        current_segments.append(segment)
        previous = segment

    flush()
    return [paragraph for paragraph in paragraphs if paragraph["text"]]


def align_paragraphs_to_segments(paragraphs, segments, language="", verbatim=False):
    aligned = []
    warnings = []
    pointer = 0
    segment_norms = [
        normalize_for_alignment(segment.text, language=language, verbatim=verbatim)
        for segment in segments
    ]

    for index, paragraph in enumerate(paragraphs, start=1):
        target = normalize_for_alignment(paragraph["text"], language=language, verbatim=verbatim)
        if not target:
            continue

        first_token = target[: min(24, len(target))]
        best_start = pointer
        best_start_score = -1.0
        for candidate in range(pointer, min(len(segments), pointer + 60)):
            candidate_text = "".join(segment_norms[candidate : min(len(segments), candidate + 8)])
            if not candidate_text:
                continue
            score = SequenceMatcher(None, first_token, candidate_text[: max(len(first_token), 1)]).ratio()
            if first_token and first_token in candidate_text:
                score += 0.5
            if score > best_start_score:
                best_start = candidate
                best_start_score = score

        accum = ""
        best_end = best_start
        best_score = -1.0
        for end in range(best_start, min(len(segments), best_start + 180)):
            accum += segment_norms[end]
            if not accum:
                continue
            ratio = SequenceMatcher(None, target, accum).ratio()
            containment_bonus = 0.25 if (target in accum or accum in target) else 0.0
            length_penalty = abs(len(accum) - len(target)) / max(len(target), 1)
            score = ratio + containment_bonus - (length_penalty * 0.15)
            if score > best_score:
                best_score = score
                best_end = end
            if len(accum) >= len(target) * 1.25 and end > best_start:
                break

        if best_score < 0.55:
            warnings.append(f"Paragraph {index} low alignment score {best_score:.2f}")
        aligned.append(
            {
                "start": segments[best_start].start,
                "end": segments[best_end].end,
                "text": paragraph["text"],
                "score": round(best_score, 4),
            }
        )
        pointer = max(best_end + 1, pointer + 1)

    return aligned, warnings


def validate_markdown_paragraphs(paragraphs):
    warnings = []
    previous_start = -1
    previous_end = -1
    for index, paragraph in enumerate(paragraphs, start=1):
        if paragraph["start"] < previous_start:
            warnings.append(f"Paragraph {index} start timestamp is not monotonic.")
        if paragraph["end"] < paragraph["start"]:
            warnings.append(f"Paragraph {index} ends before it starts.")
        if paragraph["end"] < previous_end:
            warnings.append(f"Paragraph {index} end timestamp is not monotonic.")
        if any(marker in paragraph["text"] for marker in MOJIBAKE_MARKERS):
            warnings.append(f"Paragraph {index} contains mojibake marker.")
        previous_start = paragraph["start"]
        previous_end = paragraph["end"]
    return warnings


def write_markdown(
    markdown_path,
    video_name,
    source_video,
    backend,
    language,
    audio_stream_index,
    paragraphs,
    postprocess_mode="clean",
):
    def yaml_quote(value):
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"

    lines = [
        "---",
        f"title: {yaml_quote(video_name)}",
        f"source_video: {yaml_quote(source_video)}",
        f"backend: {yaml_quote(backend)}",
        f"language: {yaml_quote(language or 'und')}",
        f"audio_stream_index: {audio_stream_index}",
        f"postprocess_mode: {yaml_quote(postprocess_mode)}",
        f"generated_at: {yaml_quote(datetime.now(timezone.utc).isoformat())}",
        "---",
        "",
        f"# {video_name}",
        "",
    ]
    for paragraph in paragraphs:
        lines.append(f"## {format_time(paragraph['start'])} - {format_time(paragraph['end'])}")
        lines.append("")
        lines.append(paragraph["text"])
        lines.append("")
    Path(markdown_path).parent.mkdir(parents=True, exist_ok=True)
    Path(markdown_path).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def postprocess_text_transcription(
    output_dir,
    audio_stem,
    video_stem,
    markdown_path,
    report_path,
    source_video,
    backend,
    requested_language="",
    audio_stream_index=-1,
    section_seconds=180,
    paragraph_max_chars=900,
    verbatim=False,
    backend_settings=None,
    backend_versions=None,
    backend_command=None,
):
    output_dir = Path(output_dir)
    copied = canonicalize_native_outputs(output_dir, audio_stem, video_stem)
    segments, detected_language, raw_json = load_segments(output_dir, audio_stem, requested_language=requested_language)
    detected_language = read_detected_language(raw_json, detected_language)
    if not segments:
        raise RuntimeError("La transcripcion no produjo texto util para generar Markdown.")
    detected_language = infer_language_from_text(segments, detected_language)

    cleaned, removed_count = clean_segments(segments, language=detected_language, verbatim=verbatim)
    if not cleaned:
        raise RuntimeError("El postproceso elimino todos los segmentos por ruido/relleno; revisa el audio o los parametros.")

    cleaned_text_outputs = write_clean_text_outputs(cleaned, output_dir, video_stem)
    initial_paragraphs = build_markdown_paragraphs(cleaned, paragraph_max_chars=paragraph_max_chars)
    aligned_paragraphs, alignment_warnings = align_paragraphs_to_segments(
        initial_paragraphs,
        cleaned,
        language=detected_language,
        verbatim=verbatim,
    )
    validation_warnings = validate_markdown_paragraphs(aligned_paragraphs)
    write_markdown(
        markdown_path=markdown_path,
        video_name=video_stem,
        source_video=source_video,
        backend=backend,
        language=detected_language,
        audio_stream_index=audio_stream_index,
        paragraphs=aligned_paragraphs,
        postprocess_mode="verbatim" if verbatim else "clean",
    )
    report = {
        "source_video": source_video,
        "backend": backend,
        "detected_language": detected_language or "und",
        "audio_stream_index": audio_stream_index,
        "postprocess_mode": "verbatim" if verbatim else "clean",
        "backend_settings": backend_settings or {},
        "backend_versions": backend_versions or {},
        "backend_command": backend_command or [],
        "input_segment_count": len(segments),
        "clean_segment_count": len(cleaned),
        "removed_segment_count": removed_count,
        "section_count": len(aligned_paragraphs),
        "markdown_paragraph_count": len(aligned_paragraphs),
        "markdown_alignment_warnings": alignment_warnings,
        "markdown_validation_warnings": validation_warnings,
        "native_outputs": copied,
        "cleaned_text_outputs": cleaned_text_outputs,
        "markdown": str(markdown_path),
    }
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="Postprocess Whisper/WhisperX outputs into RAG-ready Markdown.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--audio-stem", required=True)
    parser.add_argument("--video-stem", required=True)
    parser.add_argument("--markdown", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--source-video", required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--requested-language", default="")
    parser.add_argument("--audio-stream-index", type=int, default=-1)
    parser.add_argument("--section-seconds", type=int, default=180)
    parser.add_argument("--paragraph-max-chars", type=int, default=900)
    parser.add_argument("--verbatim", action="store_true")
    parser.add_argument("--backend-settings-json", default="{}")
    parser.add_argument("--backend-versions-json", default="{}")
    parser.add_argument("--backend-command-json", default="[]")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = postprocess_text_transcription(
        output_dir=args.output_dir,
        audio_stem=args.audio_stem,
        video_stem=args.video_stem,
        markdown_path=args.markdown,
        report_path=args.report,
        source_video=args.source_video,
        backend=args.backend,
        requested_language=args.requested_language,
        audio_stream_index=args.audio_stream_index,
        section_seconds=args.section_seconds,
        paragraph_max_chars=args.paragraph_max_chars,
        verbatim=args.verbatim,
        backend_settings=decode_json_argument(args.backend_settings_json, {}),
        backend_versions=decode_json_argument(args.backend_versions_json, {}),
        backend_command=decode_json_argument(args.backend_command_json, []),
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Markdown: {report['markdown']}")


if __name__ == "__main__":
    main()
