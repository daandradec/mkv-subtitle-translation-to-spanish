# Backends

Use `src/transcription_backend.py` as the single source for backend command construction.

- `auto`: prefer WhisperX; fallback to OpenAI Whisper.
- `whisperx`: use `large-v3`, CUDA, `float16`, and batch size 8 by default.
- `whisper`: use `turbo`, CUDA, and fp16 by default.
- Use autodetection only for the preliminary language probe. After the user confirms or corrects it, force that code in the definitive transcription.
- For maximum-quality runs, pass `-WhisperXQuality maximum`; this selects beam size 10 and patience 2 while retaining temperature 0, length penalty 1, 30-second chunks, and the default pyannote VAD thresholds.
- Force the known language explicitly for controlled comparisons. Use short, verified domain context and hotwords when available.
- Keep `balanced` as the compatibility default. Override beam size, patience, VAD, or chunk size only for measured A/B experiments.
- Do not install dependencies during the skill flow; the project setup script manages `.venv`.

If WhisperX is unavailable, surface the warning and continue with Whisper when available.
