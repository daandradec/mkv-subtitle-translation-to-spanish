---
name: video-voice-cleaner
description: "Independent workflow for cleaning, clarifying, and loudness-normalizing voices in video audio before optional Whisper or WhisperX transcription, producing a new MKV with clean FLAC audio as default while preserving original audio."
---

# Video Voice Cleaner

## Core Rule

Use this skill when a video has background noise, low voice clarity, or inconsistent loudness and the user wants a cleaner audio track before optional transcription. Do not transcribe, translate, or create subtitles in this flow.

The output is a new MKV with copied video, clean FLAC audio as the default track, and original audio preserved as a non-default fallback.

## Agent Lifecycle

Use subagents in small batches and close them after integrating results.

1. Start with `audio-container-inspector`.
2. Use `profile-designer` to choose or confirm `conservative`, `balanced`, or `asr`.
3. Run `ffmpeg-executor` only after workspace, audio stream, model path, and profile are known.
4. Run `quality-reviewer` after clean FLAC or samples exist.
5. Run `technical-validator` after final MKV/report are generated.
6. Keep at most two active subagents unless the user explicitly requests broader parallel work.

## Required References

- `agents/audio-container-inspector.md`: inspect video/audio streams and select audio.
- `agents/profile-designer.md`: choose the safest profile.
- `agents/ffmpeg-executor.md`: run the local FFmpeg pipeline.
- `agents/quality-reviewer.md`: review naturalness and ASR suitability.
- `agents/technical-validator.md`: validate MKV/audio metadata.
- `references/workflow.md`: end-to-end voice cleaning pipeline.
- `references/profiles.md`: profile behavior and tradeoffs.
- `references/testing.md`: validation matrix.

## Workflow

1. Validate input as either one video file or one folder. Folder input processes valid videos non-recursively in name order.
2. Select audio with optional `-AudioStreamIndex`; otherwise use default audio, then first audio. The same selection rule applies to every file in batch mode.
3. Use `conservative` by default unless the user asks for stronger cleanup.
4. Validate `models/voice-cleaner/std.rnnn`.
5. Run `src/clean_video_voice.ps1`.
6. Preserve original audio and mark clean FLAC as default in the output MKV.
7. Keep generated diagnostics in `subtitle_work/<workspace-id>/voice-cleaner/`.
8. Report the output MKV and clean FLAC paths. In batch mode, continue after per-file failures and summarize processed/failed items.

## Guardrails

- Do not invoke transcription automatically.
- Do not delete or modify the temporary reference project `voice_cleaner_recorder_video_flac_audio/`.
- Prefer natural voice over aggressive denoising.
- Avoid hardcoded timestamp-specific noise fixes in v1.
- Keep generated media ignored by Git.
