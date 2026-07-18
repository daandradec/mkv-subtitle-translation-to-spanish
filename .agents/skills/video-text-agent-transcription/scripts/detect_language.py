#!/usr/bin/env python3
import argparse
import itertools
import json
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path


def run_json_command(command):
    completed = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
    return json.loads(completed.stdout)


def inspect_media(input_path):
    payload = run_json_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type:stream_disposition=default",
            "-of",
            "json",
            str(input_path),
        ]
    )
    duration = float(payload.get("format", {}).get("duration") or 0)
    audio_streams = [stream for stream in payload.get("streams", []) if stream.get("codec_type") == "audio"]
    if not audio_streams:
        raise RuntimeError("El archivo no contiene una pista de audio.")
    return duration, audio_streams


def select_audio_stream(audio_streams, requested_index=-1):
    if requested_index >= 0:
        for stream in audio_streams:
            if int(stream["index"]) == requested_index:
                return int(stream["index"])
        raise RuntimeError(f"No existe la pista de audio con indice {requested_index}.")
    for stream in audio_streams:
        disposition = stream.get("disposition") or {}
        if int(disposition.get("default") or 0) == 1:
            return int(stream["index"])
    return int(audio_streams[0]["index"])


def build_probe_offsets(duration, sample_duration=30.0, sample_count=3):
    if duration <= 0 or duration <= sample_duration * 1.5 or sample_count <= 1:
        return [0.0]
    max_start = max(0.0, duration - sample_duration)
    fractions = [0.05, 0.5, 0.9]
    if sample_count > len(fractions):
        fractions = [index / (sample_count - 1) for index in range(sample_count)]
    else:
        fractions = fractions[:sample_count]
    offsets = sorted({round(max_start * fraction, 3) for fraction in fractions})
    return offsets or [0.0]


def aggregate_samples(samples):
    if not samples:
        raise RuntimeError("Whisper no produjo una deteccion de idioma util.")
    counts = Counter(sample["language"] for sample in samples)
    probability_sums = defaultdict(float)
    for sample in samples:
        probability_sums[sample["language"]] += float(sample["probability"])
    language = max(counts, key=lambda code: (counts[code], probability_sums[code]))
    matching = [sample for sample in samples if sample["language"] == language]
    confidence = sum(float(sample["probability"]) for sample in matching) / len(matching)
    return language, confidence


def extract_probe(input_path, output_path, stream_index, offset, duration):
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            str(offset),
            "-t",
            str(duration),
            "-i",
            str(input_path),
            "-map",
            f"0:{stream_index}",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ],
        check=True,
    )


def detect_language(args):
    for executable in ("ffmpeg", "ffprobe"):
        if shutil.which(executable) is None:
            raise RuntimeError(f"{executable} no esta disponible en PATH.")

    from faster_whisper import WhisperModel
    from whisperx.utils import LANGUAGES

    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        raise RuntimeError(f"No se encontro el archivo: {input_path}")

    duration, audio_streams = inspect_media(input_path)
    stream_index = select_audio_stream(audio_streams, args.audio_stream_index)
    offsets = build_probe_offsets(duration, args.sample_duration, args.sample_count)
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    samples = []

    with tempfile.TemporaryDirectory(prefix="whisper-language-probe-") as temp_dir:
        temp_root = Path(temp_dir)
        for index, offset in enumerate(offsets, start=1):
            probe_path = temp_root / f"probe-{index}.wav"
            extract_probe(input_path, probe_path, stream_index, offset, args.sample_duration)
            segments, info = model.transcribe(
                str(probe_path),
                language=None,
                task="transcribe",
                beam_size=1,
                best_of=1,
                temperature=0,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            list(itertools.islice(segments, 1))
            samples.append(
                {
                    "offset": offset,
                    "language": info.language,
                    "probability": round(float(info.language_probability), 6),
                }
            )

    language, confidence = aggregate_samples(samples)
    matching_count = sum(1 for sample in samples if sample["language"] == language)
    sample_agreement = matching_count / len(samples)
    disagreement = matching_count != len(samples)
    return {
        "input": str(input_path),
        "audio_stream_index": stream_index,
        "language": language,
        "backend_language_name": LANGUAGES.get(language, language),
        "confidence": round(confidence, 6),
        "sample_agreement": round(sample_agreement, 6),
        "disagreement": disagreement,
        "uncertain": confidence < 0.60 or disagreement,
        "sample_count": len(samples),
        "samples": samples,
    }


def main():
    parser = argparse.ArgumentParser(description="Detect a video's spoken language before transcription.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--compute-type", default="float16")
    parser.add_argument("--audio-stream-index", type=int, default=-1)
    parser.add_argument("--sample-duration", type=float, default=30.0)
    parser.add_argument("--sample-count", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = detect_language(args)
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['language']} ({result['backend_language_name']}), confidence={result['confidence']:.2f}")


if __name__ == "__main__":
    main()
