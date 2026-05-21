# Technical Validator

## Purpose

Validate final voice-cleaned outputs.

## Inputs

- Final MKV path.
- Clean FLAC path.
- Report path.

## Tasks

- Use `ffprobe` to confirm clean FLAC exists in the MKV.
- Confirm clean audio is default.
- Confirm original audio is still present.
- Confirm video stream exists and was not unnecessarily re-encoded.
- Confirm `voice_cleaner_report.json` exists.

## Output Contract

Return concise validation with stream metadata and any residual risks.
