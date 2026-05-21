# Testing

## Unit Tests

- Workspace id and output paths.
- Backend selection:
  - WhisperX preferred;
  - Whisper fallback warning;
  - clear error if no backend exists.
- Postprocess:
  - rejects missing/empty SRT;
  - writes clean SRT and simple ASS;
  - writes language metadata and translation warning.

## Script Checks

- Parse `src/init_python_env.ps1`.
- Parse `src/transcribe_video_audio.ps1`.
- `py_compile` all new Python modules.
- Validate that missing Python 3.12 fails with a clear installation message.
- Use `-DryRun` to inspect backend command without transcription.

## Manual Validation

- Run against a short MKV and a short MP4 without subtitles.
- Confirm generated MKV includes a default transcribed subtitle track.
- Open or extract the embedded SRT and sample readable text.
- Pass the generated MKV to `mkv-subtitle-agentic-translation` when the detected language is supported.
