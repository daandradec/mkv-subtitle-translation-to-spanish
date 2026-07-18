# Transcription Runner

Execute the local backend through `src/transcribe_video_text.ps1`.

- Prefer `-Backend auto` so WhisperX is used first and Whisper is fallback.
- Keep `-Language` empty unless the user explicitly wants to force a language.
- Use `.venv` through the project scripts; do not call global Python directly.
- For batch jobs, let failed videos be reported while successful videos continue.
