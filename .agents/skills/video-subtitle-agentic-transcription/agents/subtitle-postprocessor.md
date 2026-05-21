# Subtitle Postprocessor

## Purpose

Clean backend subtitle output and prepare files for MKV muxing and later translation.

## Inputs

- Raw backend SRT and JSON.
- Output paths for SRT, ASS, and report.

## Tasks

- Remove empty cues and validate increasing cue times.
- Write clean SRT to `output/<workspace-id>/`.
- Convert SRT to simple ASS with `src/subtitle_text_to_ass.py` compatible formatting.
- Produce `transcription_report.json` with backend, language, cue count, and translation compatibility warning.

## Output Contract

Return paths to clean SRT, ASS, report, cue count, language metadata, and warnings.
