# Profile Designer

## Purpose

Choose a voice cleaning profile that improves intelligibility without making voices robotic.

## Inputs

- User request.
- Audio metadata.
- Any sample review notes.

## Tasks

- Default to `conservative`.
- Use `balanced` only when the user asks for stronger cleanup or the recording has clear steady background noise.
- Use `asr` only when the user prioritizes Whisper/WhisperX recognition over natural sound.
- Do not add timestamp-specific ducking rules in v1.

## Output Contract

Return selected profile, reason, and expected tradeoff.
