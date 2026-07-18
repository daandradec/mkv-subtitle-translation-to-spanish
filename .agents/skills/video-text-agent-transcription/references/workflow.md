# Workflow

1. Resolve input as a file, folder, or strict autodetection from `input/`.
2. Validate each candidate with `ffprobe` and require both video and audio.
3. Initialize `.venv` with Python 3.12 through `src/init_python_env.ps1`.
4. Create a unique workspace using the same `24 + "-" + 6` identifier pattern used by the other video skills.
5. Extract the selected audio stream to mono 16 kHz WAV in `subtitle_work/<workspace-id>/text-transcription/`.
6. Run WhisperX or Whisper fallback with `--output_format all`.
7. Normalize native output names to `<videoname>.*`.
8. Generate `<videoname>.md` and `text_transcription_report.json`.
9. For batch mode, continue after per-video failures and return a final failure status if any video failed.

Do not remux video and do not create embedded subtitles in this skill.
