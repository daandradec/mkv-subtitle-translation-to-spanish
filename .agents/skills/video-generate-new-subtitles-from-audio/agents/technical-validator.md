# Technical Validator

## Purpose

Validate generated transcription subtitle files and the final MKV output.

## Inputs

- Internal postprocessed SRT path and optional exported ASS path.
- Final transcribed MKV path.
- Original source video path.
- `transcription_report.json`.

## Tasks

- Verify SRT cue count is nonzero.
- Confirm no same-stem SRT/ASS exists beside the final MKV in the default mode.
- When ASS export is requested, verify it was derived from the embedded track, contains matching Dialogue events, and is stored under the separate `sidecars/` directory.
- Use `ffprobe` to confirm the output MKV has the new subtitle track, title, language, and default flag.
- Confirm all source stream types/counts are preserved and exactly one transcription subtitle stream was added.
- Compare source SRT cue starts with embedded packet timestamps. Every cue must receive one uniform mux shift with no more than 5 ms spread.
- Extract the embedded subtitle track and sample readable text.
- Confirm the final MKV is in `outputs/<stem>/`, internal SRT is under `outputs/<stem>/debug/video-generate-new-subtitles-from-audio/`, and optional ASS is in `outputs/<stem>/sidecars/`.

## Output Contract

Return pass/fail, stream metadata summary, cue counts, samples, and actionable fixes.
