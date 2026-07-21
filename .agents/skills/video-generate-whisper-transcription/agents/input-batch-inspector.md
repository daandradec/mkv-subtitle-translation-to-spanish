# Input Batch Inspector

Validate the requested input before transcription.

- Accept one video file or one folder.
- For folder input, enumerate files non-recursively and keep only videos with audio that FFmpeg can inspect.
- Report zero-video, no-audio, or ambiguous input failures clearly.
- Recommend `-AudioStreamIndex` only when multiple plausible audio tracks exist and the default looks wrong.
