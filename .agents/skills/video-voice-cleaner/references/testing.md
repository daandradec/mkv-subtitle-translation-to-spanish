# Testing

## Unit Tests

- Workspace id and paths.
- Profile validation.
- Filter chain per profile.
- RNNoise model path in filter chain.
- Loudnorm JSON extraction.
- Loudnorm second pass filter generation.

## Script Checks

- Parse `src/video-voice-cleaner/clean_video_voice.ps1`.
- Compile Python sources under `src/shared/python/` and `src/video-voice-cleaner/python/`.
- Run `-DryRun` on one real video.

## Manual Validation

- `ffprobe` final MKV.
- Clean FLAC track is default.
- Original audio remains present.
- Voice sounds natural on conservative profile.
- Output MKV can be used manually by `video-subtitle-agentic-transcription`.
