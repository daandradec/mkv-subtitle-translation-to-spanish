# Workflow

1. Resolve input as a file, folder, or strict autodetection from `input/`.
2. Validate each candidate with `ffprobe` and require both video and audio.
3. Initialize `.venv` with Python 3.12 through `src/init_python_env.ps1`.
4. Detect the spoken language with `scripts/detect_language.py`, unless the user supplied a proposed language.
5. Show the detected/proposed code, Spanish name, confidence when available, and the complete Whisper language catalog. Ask the user to confirm or correct it and wait.
6. Create a unique workspace using the same `24 + "-" + 6` identifier pattern used by the other video skills.
7. Extract the selected audio stream to mono 16 kHz WAV in `subtitle_work/<workspace-id>/text-transcription/`.
8. Run WhisperX or Whisper fallback with `--language <confirmed-code>` and `--output_format all`.
9. Normalize native output names to `<videoname>.*`.
10. Generate `<videoname>.md` and `text_transcription_report.json`.
11. For batch mode, continue after per-video failures and return a final failure status if any video failed.

Do not remux video and do not create embedded subtitles in this skill.
