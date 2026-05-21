#!/usr/bin/env python3
import argparse
import json
import shutil
from pathlib import Path


INSTALL_WHISPERX_MESSAGE = (
    "WhisperX no esta disponible en el entorno virtual local; se usara openai-whisper desde .venv."
)


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
    device="cuda",
    compute_type="float16",
    batch_size=8,
    fp16=True,
):
    audio = str(audio)
    output_dir = str(output_dir)
    if backend == "whisperx":
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
            "--output_dir",
            output_dir,
            "--output_format",
            "all",
        ]
        if language:
            command.extend(["--language", language])
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
        device=args.device,
        compute_type=args.compute_type,
        batch_size=args.batch_size,
        fp16=args.fp16,
    )
    return {
        "backend": backend,
        "warning": warning,
        "command": command,
    }


def main():
    parser = argparse.ArgumentParser(description="Resolve transcription backend and command.")
    parser.add_argument("--backend", choices=["auto", "whisperx", "whisper"], default="auto")
    parser.add_argument("--audio", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--language", default="")
    parser.add_argument("--whisperx-model", default="large-v3")
    parser.add_argument("--whisper-model", default="turbo")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--compute-type", default="float16")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--fp16", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        payload = resolve_backend_payload(args)
    except RuntimeError as exc:
        raise SystemExit(str(exc))

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if payload["warning"]:
            print(payload["warning"])
        print(" ".join(payload["command"]))


if __name__ == "__main__":
    main()
