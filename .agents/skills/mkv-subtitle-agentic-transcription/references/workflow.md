# Workflow

## 1. Prepare Input

- Use `input/` as the canonical folder.
- Process only one MKV per run.
- Initialize `.venv/` with Python 3.12 using `src/init_python_env.ps1` before running Python modules or transcription executables.
- Use `.venv/Scripts` first in PATH so `whisperx` and `whisper` come from the project environment.
- Create shared workspace directories:
  - `subtitle_work/<workspace-id>/`
  - `output/<workspace-id>/`
- Use the same `24 + "-" + 6` workspace id rule used by translation.

## 2. Inspect Audio

- Use `ffprobe` to inspect audio streams.
- Select requested audio index when provided.
- Otherwise select default audio, then first audio.
- Stop if no audio streams exist.

## 3. Extract Audio

- Extract WAV mono 16 kHz with FFmpeg.
- Keep audio in `subtitle_work/<workspace-id>/`.

## 4. Transcribe

- Prefer WhisperX installed in `.venv/`.
- Fallback to `openai-whisper` installed in `.venv/` if WhisperX is missing.
- Preserve original spoken language.
- Do not use translation mode.
- Keep raw outputs in `subtitle_work/<workspace-id>/whisper/`.

## 5. Postprocess

- Clean SRT cues and reject empty transcription.
- Generate simple ASS from SRT.
- Write `transcription_report.json`.

## 6. Remux

- Use `mkvmerge`.
- Preserve original tracks.
- Embed the transcribed SRT as default with title `Transcripción <idioma>`.

## 7. Handoff

- The generated MKV can be passed to `mkv-subtitle-agentic-translation`.
- If detected language is unsupported by translation, report that transcription succeeded but translation may stop.
