# Workflow

## 1. Prepare Input

- Use `input/` as the canonical folder.
- Process only one video per run.
- Accept any video file with audio that FFmpeg/Whisper can decode. Common examples include MKV, MP4, MOV, M4V, WebM, AVI, WMV, FLV, TS/M2TS, MPEG/MPG, 3GP/3G2, and OGV.
- Initialize `.venv/` with Python 3.12 using `src/init_python_env.ps1` before running Python modules or transcription executables.
- Use `.venv/Scripts` first in PATH so `whisperx` and `whisper` come from the project environment.
- Create shared workspace directories:
  - `subtitle_work/<workspace-id>/`
  - `output/<workspace-id>/`
- Use the same `24 + "-" + 6` workspace id rule used by translation.

## 2. Inspect Audio

- Use `ffprobe` to inspect audio streams.
- Select requested audio index when the optional `-AudioStreamIndex` parameter is provided.
- Otherwise select default audio, then first audio.
- If multiple audio streams are marked default, use the first one in container order and warn that `-AudioStreamIndex` can override the choice.
- If `-Language` is not provided, derive the backend language from the selected audio stream metadata and pass it explicitly to WhisperX/Whisper.
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
- Limit visible subtitles to two lines per cue.
- Split long cues into sequential cues inside the same original time range instead of stacking three or more lines.
- Prefer WhisperX word timestamps for split cue start/end times; if unavailable, distribute timing proportionally inside the original cue.
- Keep ASS companion subtitles constrained to about 80% of video width by using 10% side margins.
- Generate simple ASS from SRT.
- Write `transcription_report.json`.

## 6. Remux

- Output must always be an MKV.
- Use `mkvmerge` directly when it can read the source container.
- If `mkvmerge` cannot read the source container directly, first create an intermediate MKV with `ffmpeg -map 0 -c copy`, then add the transcription track with `mkvmerge`.
- Preserve original tracks when the source container allows copy remuxing.
- Embed the transcribed SRT as default with title `Transcripción <idioma>`.

## 7. Handoff

- The generated MKV can be passed to `mkv-subtitle-agentic-translation`.
- If detected language is unsupported by translation, report that transcription succeeded but translation may stop.
