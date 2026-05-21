# Backends

## WhisperX Preferred

WhisperX is preferred for timestamp quality, VAD, alignment, and batching. Run it from the project `.venv/` created with Python 3.12; do not rely on a global Python 3.14 install.

Default command shape:

```powershell
whisperx "<audio.wav>" --model large-v3 --device cuda --compute_type float16 --batch_size 8 --output_dir "<workdir>" --output_format all
```

Add `--language <code>` when the user provides `-Language` or when the selected audio stream metadata can be mapped to a Whisper language code.

## openai-whisper Fallback

Use `openai-whisper` from `.venv/` when WhisperX is not installed or not available in the local environment.

Default command shape:

```powershell
whisper "<audio.wav>" --model turbo --task transcribe --device cuda --fp16 True --output_dir "<workdir>" --output_format all
```

When fallback is used, report:

```text
WhisperX no esta disponible en `.venv`; se uso openai-whisper desde el entorno local.
```

## Constraints

- Do not install dependencies globally.
- Use `requirements.txt` through `src/init_python_env.ps1` for required local dependencies.
- Use `requirements-whisperx.txt` for the preferred WhisperX backend; fallback to openai-whisper remains valid if WhisperX installation fails.
- Do not require API keys.
- Do not use diarization in v1.
- Do not use `--task translate`.
