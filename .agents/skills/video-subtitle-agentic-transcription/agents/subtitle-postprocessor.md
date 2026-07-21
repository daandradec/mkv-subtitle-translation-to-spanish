# Subtitle Postprocessor

## Purpose

Clean backend subtitle output and prepare files for MKV muxing and later translation.

## Inputs

- Raw backend SRT and JSON.
- Internal output path for SRT and report.

## Tasks

- Remove empty cues and validate increasing cue times.
- Write clean SRT to `output/<stem>/debug/video-subtitle-agentic-transcription/postprocess/` as an internal remux input.
- Do not publish SRT or ASS beside the final MKV. An optional ASS export is created only after remux from the embedded normalized track.
- Produce `transcription_report.json` with backend, language, cue count, and translation compatibility warning.

## Output Contract

Return paths to the internal clean SRT and report, cue count, language metadata, and warnings.
