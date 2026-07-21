# FFmpeg Executor

## Purpose

Run the local voice cleaning pipeline.

## Inputs

- Source video path.
- Selected audio stream index.
- Workspace paths.
- Profile.
- RNNoise model path.

## Tasks

- Run `src/video-voice-cleaner/clean_video_voice.ps1`.
- Use FFmpeg/FFprobe/MKVToolNix from PATH.
- Keep video copied whenever possible.
- Write clean FLAC and remux MKV.
- Preserve original audio as non-default.
- Keep logs under `output/<stem>/debug/video-voice-cleaner/`.

## Output Contract

Return exact command, output paths, report path, and any warnings.
