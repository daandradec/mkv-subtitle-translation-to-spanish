# Workflow

## 1. Prepare Input

- Use `input/` as the canonical folder.
- Process a single video when a file is provided.
- Process all valid videos non-recursively when a folder path is provided.
- Without explicit input, keep strict autodetection: process only when `input/` contains exactly one valid video.
- Accept any video file with audio that FFmpeg can decode.
- Use deterministic `output/<stem>/` and keep helpers under `output/<stem>/debug/video-voice-cleaner/`.
- A fresh run safely clears the corresponding output directory. In batch mode, reject duplicate filename stems before processing and continue with remaining videos if an individual run fails.

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
