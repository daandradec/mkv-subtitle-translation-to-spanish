# Workflow

## 1. Prepare Input

- Use `input/` as the canonical folder.
- Process a single video when a file is provided.
- Process all valid videos non-recursively when a folder path is provided.
- Without explicit input, keep strict autodetection: process only when `input/` contains exactly one valid video.
- Accept any video file with audio that FFmpeg can decode.
- Create shared workspace directories:
  - `subtitle_work/<workspace-id>/voice-cleaner/`
  - `output/<workspace-id>/`
- In batch mode, create one independent workspace per video and continue with remaining videos if one fails.

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
