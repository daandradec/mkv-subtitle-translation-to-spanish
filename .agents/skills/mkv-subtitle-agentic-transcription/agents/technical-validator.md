# Technical Validator

## Purpose

Validate generated transcription subtitle files and the final MKV.

## Inputs

- Final SRT/ASS paths.
- Final transcribed MKV path.
- `transcription_report.json`.

## Tasks

- Verify SRT cue count is nonzero.
- Verify ASS contains matching Dialogue events.
- Use `ffprobe` to confirm the MKV has the new subtitle track, title, language, and default flag.
- Extract the embedded subtitle track and sample readable text.
- Confirm generated files are in `output/<workspace-id>/`.

## Output Contract

Return pass/fail, stream metadata summary, cue counts, samples, and actionable fixes.
