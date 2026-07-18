# Backends

Use `src/transcription_backend.py` as the single source for backend command construction.

- `auto`: prefer WhisperX; fallback to OpenAI Whisper.
- `whisperx`: use `large-v3`, CUDA, `float16`, and batch size 8 by default.
- `whisper`: use `turbo`, CUDA, and fp16 by default.
- Leave language empty for autodetection unless the user explicitly passes one.
- Do not install dependencies during the skill flow; the project setup script manages `.venv`.

If WhisperX is unavailable, surface the warning and continue with Whisper when available.
