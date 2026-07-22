#!/usr/bin/env python3
import argparse
import importlib.metadata
import json
import os
import shutil
from pathlib import Path


INSTALL_WHISPERX_MESSAGE = (
    "WhisperX no esta disponible en el entorno virtual local; se usara openai-whisper desde .venv."
)

WHISPERX_QUALITY_PROFILES = {
    "balanced": {
        "beam_size": 5,
        "patience": 1.0,
    },
    "maximum": {
        "beam_size": 10,
        "patience": 2.0,
    },
}


def package_versions():
    versions = {}
    for package in ("whisperx", "faster-whisper", "ctranslate2", "torch"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            continue
    return versions


def resolve_whisperx_decoding_options(quality="balanced", beam_size=None, patience=None):
    if quality not in WHISPERX_QUALITY_PROFILES:
        choices = ", ".join(WHISPERX_QUALITY_PROFILES)
        raise ValueError(f"Perfil WhisperX no soportado: {quality}. Usa {choices}.")
    profile = WHISPERX_QUALITY_PROFILES[quality]
    resolved_beam_size = profile["beam_size"] if beam_size is None else beam_size
    resolved_patience = profile["patience"] if patience is None else patience
    if resolved_beam_size < 1:
        raise ValueError("WhisperX beam_size debe ser mayor o igual a 1.")
    if resolved_patience <= 0:
        raise ValueError("WhisperX patience debe ser mayor que 0.")
    return {
        "beam_size": int(resolved_beam_size),
        "patience": float(resolved_patience),
    }


def validate_whisperx_segmentation(vad_onset, vad_offset, chunk_size):
    for name, value in (("vad_onset", vad_onset), ("vad_offset", vad_offset)):
        if not 0 <= value <= 1:
            raise ValueError(f"WhisperX {name} debe estar entre 0 y 1.")
    if chunk_size < 1 or chunk_size > 30:
        raise ValueError("WhisperX chunk_size debe estar entre 1 y 30 segundos.")


def executable_exists(name, resolver=shutil.which):
    return resolver(name) is not None


def choose_backend(preferred="auto", resolver=shutil.which):
    preferred = preferred.casefold()
    has_whisperx = executable_exists("whisperx", resolver)
    has_whisper = executable_exists("whisper", resolver)

    if preferred == "whisperx":
        if not has_whisperx:
            raise RuntimeError("WhisperX no esta instalado. Instala con `pip install whisperx` o `uvx whisperx`.")
        return "whisperx", ""
    if preferred == "whisper":
        if not has_whisper:
            raise RuntimeError("openai-whisper no esta instalado o `whisper` no esta en PATH.")
        return "whisper", ""
    if preferred != "auto":
        raise RuntimeError(f"Backend no soportado: {preferred}. Usa auto, whisperx o whisper.")

    if has_whisperx:
        return "whisperx", ""
    if has_whisper:
        return "whisper", INSTALL_WHISPERX_MESSAGE
    raise RuntimeError("No se encontro WhisperX ni openai-whisper en PATH.")


def bool_arg(value):
    return "True" if bool(value) else "False"


def build_backend_command(
    backend,
    audio,
    output_dir,
    language="",
    whisperx_model="large-v3",
    whisper_model="turbo",
    whisper_model_dir="",
    device="cuda",
    compute_type="float16",
    batch_size=8,
    fp16=True,
    whisperx_quality="balanced",
    whisperx_beam_size=None,
    whisperx_patience=None,
    whisperx_length_penalty=1.0,
    whisperx_initial_prompt="",
    whisperx_hotwords="",
    whisperx_vad_method="pyannote",
    whisperx_vad_onset=0.5,
    whisperx_vad_offset=0.363,
    whisperx_chunk_size=30,
):
    audio = str(audio)
    output_dir = str(output_dir)
    if backend == "whisperx":
        validate_whisperx_segmentation(
            whisperx_vad_onset,
            whisperx_vad_offset,
            whisperx_chunk_size,
        )
        decoding = resolve_whisperx_decoding_options(
            quality=whisperx_quality,
            beam_size=whisperx_beam_size,
            patience=whisperx_patience,
        )
        command = [
            "whisperx",
            audio,
            "--model",
            whisperx_model,
            "--device",
            device,
            "--compute_type",
            compute_type,
            "--batch_size",
            str(batch_size),
            "--beam_size",
            str(decoding["beam_size"]),
            "--patience",
            str(decoding["patience"]),
            "--length_penalty",
            str(whisperx_length_penalty),
            "--temperature",
            "0",
            "--condition_on_previous_text",
            "False",
            "--vad_method",
            whisperx_vad_method,
            "--vad_onset",
            str(whisperx_vad_onset),
            "--vad_offset",
            str(whisperx_vad_offset),
            "--chunk_size",
            str(whisperx_chunk_size),
            "--output_dir",
            output_dir,
            "--output_format",
            "all",
        ]
        if language:
            command.extend(["--language", language])
        if whisperx_initial_prompt:
            command.extend(["--initial_prompt", whisperx_initial_prompt])
        if whisperx_hotwords:
            command.extend(["--hotwords", whisperx_hotwords])
        return command

    if backend == "whisper":
        command = [
            "whisper",
            audio,
            "--model",
            whisper_model,
            "--task",
            "transcribe",
            "--device",
            device,
            "--fp16",
            bool_arg(fp16),
            "--output_dir",
            output_dir,
            "--output_format",
            "all",
            "--verbose",
            "False",
        ]
        if whisper_model_dir:
            command.extend(["--model_dir", str(whisper_model_dir)])
        if language:
            command.extend(["--language", language])
        return command

    raise RuntimeError(f"Backend no soportado: {backend}.")


def resolve_backend_payload(args):
    backend, warning = choose_backend(args.backend)
    command = build_backend_command(
        backend=backend,
        audio=Path(args.audio),
        output_dir=Path(args.output_dir),
        language=args.language,
        whisperx_model=args.whisperx_model,
        whisper_model=args.whisper_model,
        whisper_model_dir=args.whisper_model_dir,
        device=args.device,
        compute_type=args.compute_type,
        batch_size=args.batch_size,
        fp16=args.fp16,
        whisperx_quality=args.whisperx_quality,
        whisperx_beam_size=args.whisperx_beam_size,
        whisperx_patience=args.whisperx_patience,
        whisperx_length_penalty=args.whisperx_length_penalty,
        whisperx_initial_prompt=args.whisperx_initial_prompt,
        whisperx_hotwords=args.whisperx_hotwords,
        whisperx_vad_method=args.whisperx_vad_method,
        whisperx_vad_onset=args.whisperx_vad_onset,
        whisperx_vad_offset=args.whisperx_vad_offset,
        whisperx_chunk_size=args.whisperx_chunk_size,
    )
    settings = {
        "backend": backend,
        "model": args.whisperx_model if backend == "whisperx" else args.whisper_model,
        "language": args.language or "auto",
        "device": args.device,
        "compute_type": args.compute_type if backend == "whisperx" else ("float16" if args.fp16 else "float32"),
    }
    if backend == "whisperx":
        decoding = resolve_whisperx_decoding_options(
            quality=args.whisperx_quality,
            beam_size=args.whisperx_beam_size,
            patience=args.whisperx_patience,
        )
        settings.update(
            {
                "batch_size": args.batch_size,
                "quality_profile": args.whisperx_quality,
                "beam_size": decoding["beam_size"],
                "patience": decoding["patience"],
                "length_penalty": args.whisperx_length_penalty,
                "temperature": 0,
                "condition_on_previous_text": False,
                "initial_prompt": args.whisperx_initial_prompt or None,
                "hotwords": args.whisperx_hotwords or None,
                "vad_method": args.whisperx_vad_method,
                "vad_onset": args.whisperx_vad_onset,
                "vad_offset": args.whisperx_vad_offset,
                "chunk_size": args.whisperx_chunk_size,
            }
        )
    return {
        "backend": backend,
        "warning": warning,
        "command": command,
        "settings": settings,
        "versions": package_versions(),
    }


def main():
    parser = argparse.ArgumentParser(description="Resolve transcription backend and command.")
    parser.add_argument("--backend", choices=["auto", "whisperx", "whisper"], default="auto")
    parser.add_argument("--audio", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--language", default="")
    parser.add_argument("--whisperx-model", default="large-v3")
    parser.add_argument("--whisper-model", default="turbo")
    parser.add_argument("--whisper-model-dir", default=os.environ.get("WHISPER_CACHE_DIR", ""))
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--compute-type", default="float16")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--whisperx-quality", choices=sorted(WHISPERX_QUALITY_PROFILES), default="balanced")
    parser.add_argument("--whisperx-beam-size", type=int)
    parser.add_argument("--whisperx-patience", type=float)
    parser.add_argument("--whisperx-length-penalty", type=float, default=1.0)
    parser.add_argument("--whisperx-initial-prompt", default="")
    parser.add_argument("--whisperx-hotwords", default="")
    parser.add_argument("--whisperx-vad-method", choices=["pyannote", "silero"], default="pyannote")
    parser.add_argument("--whisperx-vad-onset", type=float, default=0.5)
    parser.add_argument("--whisperx-vad-offset", type=float, default=0.363)
    parser.add_argument("--whisperx-chunk-size", type=int, default=30)
    parser.add_argument("--fp16", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        payload = resolve_backend_payload(args)
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc))

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if payload["warning"]:
            print(payload["warning"])
        print(" ".join(payload["command"]))


if __name__ == "__main__":
    main()
