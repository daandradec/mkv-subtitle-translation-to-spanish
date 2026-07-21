# Transcription Runner

## Purpose

Run the local transcription backend and produce raw SRT/JSON outputs.

## Inputs

- Extracted WAV path.
- Workspace paths.
- Backend policy, optional `-AudioStreamIndex`, and optional language.

## Tasks

- Prefer WhisperX from `.venv/Scripts`.
- If WhisperX is missing after local setup, use `openai-whisper` from `.venv/Scripts` and include the fallback warning.
- Run transcription only, never translation.
- Pass the resolved language from the selected audio stream to WhisperX/Whisper when the user did not provide `-Language`.
- Keep raw backend outputs in `output/<stem>/debug/video-generate-new-subtitles-from-audio/whisper/`.
- Do not install packages globally or require API keys.

## Output Contract

Return backend used, exact command, raw output paths, detected language when available, and any warnings.
