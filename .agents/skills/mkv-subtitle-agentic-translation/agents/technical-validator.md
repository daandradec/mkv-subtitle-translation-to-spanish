# Technical Validator

## Purpose

Validate generated subtitle files and final MKV outputs for stream metadata, readability, timing integrity, TV-safe behavior, and absence of visible ASS garbage.

## When to Spawn

Spawn after the main agent generates subtitle files and remuxes the final MKV.

## Inputs

- Final MKV path in `/output`.
- Generated subtitle file paths.
- Expected language/title/default-track policy.
- Known risky timestamps.

## Tasks

- Use `ffprobe` to verify subtitle streams, language tags, titles, and default flags.
- Extract the Spanish subtitle track from the final MKV and sample readable Spanish.
- Scan visible text for ASS commands, drawing paths, long numeric sequences, or empty translated tracks.
- Check known dialogue and song timestamps.
- Verify `/output` contains final deliverables and no required artifact is missing.

## Output Contract

Return `validation_report.md` with:

- pass/fail status;
- exact failed file paths and timestamps;
- stream metadata summary;
- extracted subtitle samples;
- recommended fixes.

## Acceptance Criteria

- The main agent can decide release readiness from the report.
- Failures are actionable and tied to concrete artifacts.
