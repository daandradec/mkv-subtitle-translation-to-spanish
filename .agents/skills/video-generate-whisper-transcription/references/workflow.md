# Workflow

1. Resolve input as a file, folder, or strict autodetection from `input/`.
2. Validate each candidate with `ffprobe` and require both video and audio.
3. Initialize `.venv` with Python 3.12 through `src/shared/powershell/init_python_env.ps1`.
4. Detect the spoken language with `scripts/detect_language.py`, unless the user supplied a proposed language.
5. Show the detected/proposed code, Spanish name, confidence when available, and the complete Whisper language catalog. Ask the user to confirm or correct it and wait.
6. Use deterministic `output/<stem>/`, where `<stem>` is the exact source filename without extension. Clear it on every fresh run; reject duplicate stems in folder mode.
7. Extract the selected audio stream to mono 16 kHz WAV in `output/<stem>/debug/video-generate-whisper-transcription/audio/`.
8. Run WhisperX or Whisper fallback with `--language <confirmed-code>` and `--output_format all`.
9. Keep all native backend formats in `output/<stem>/debug/video-generate-whisper-transcription/whisper/raw/` and clean auxiliary VTT/TXT in `whisper/postprocess/`.
10. Publish only `<videoname>.srt` and `<videoname>.md` in `output/<stem>/`; keep the technical report under `reports/`.
11. For batch mode, continue after per-video failures and return a final failure status if any video failed.

Do not remux video and do not create embedded subtitles in this skill.
