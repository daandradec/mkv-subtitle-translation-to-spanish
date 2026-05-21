# Workflow

## 1. Prepare Input

- Use `input/` as the canonical folder.
- Process only one video per run.
- Accept any video file with audio that FFmpeg can decode.
- Create shared workspace directories:
  - `subtitle_work/<workspace-id>/voice-cleaner/`
  - `output/<workspace-id>/`

## 2. Inspect Audio

- Use `ffprobe` to inspect audio streams.
- Select `-AudioStreamIndex` when provided.
- Otherwise select default audio, then first audio.
- Stop if no audio streams exist.

## 3. Clean Audio

- Validate `models/voice-cleaner/std.rnnn`.
- Build the filter chain for `conservative`, `balanced`, or `asr`.
- Create a premaster FLAC.
- Run loudness normalization in two passes.
- Write final clean FLAC.

## 4. Remux

- Output must be MKV.
- Preserve original tracks.
- Disable default on original audio tracks.
- Add clean FLAC as default with title `Voz limpia FLAC`.

## 5. Handoff

- The generated MKV can be passed manually to `video-subtitle-agentic-transcription`.
- Do not start transcription automatically.
