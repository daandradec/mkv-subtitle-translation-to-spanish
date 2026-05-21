# Testing

## Unit Tests

- Workspace id and paths.
- Profile validation.
- Filter chain per profile.
- RNNoise model path in filter chain.
- Loudnorm JSON extraction.
- Loudnorm second pass filter generation.

## Script Checks

- Parse `src/clean_video_voice.ps1`.
- `python -m py_compile src/*.py`.
- Run `-DryRun` on one real video.

## Manual Validation

- `ffprobe` final MKV.
- Clean FLAC track is default.
- Original audio remains present.
- Voice sounds natural on conservative profile.
- Output MKV can be used manually by `video-subtitle-agentic-transcription`.
