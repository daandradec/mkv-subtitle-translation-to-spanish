# Technical Validator

## Purpose

Validate generated subtitle files and final MKV outputs for stream metadata, readability, timing integrity, TV-safe behavior, and absence of visible ASS garbage.

## When to Spawn

Spawn after the main agent generates subtitle files and remuxes the final MKV.

## Inputs

- Final MKV path in `outputs/<stem>/`.
- Generated subtitle file paths.
- Expected language/title/default-track policy.
- Known risky timestamps.

## Tasks

- Use `ffprobe` to verify subtitle streams, language tags, titles, and default flags.
- Extract the Spanish subtitle track from the final MKV and sample readable Spanish.
- Scan visible text for ASS commands, drawing paths, long numeric sequences, or empty translated tracks.
- Check known dialogue and song timestamps.
- Verify the final MKV is the only file at the root of `outputs/<stem>/` and generated ASS/SRT helpers exist only under `debug/video-generate-traslated-subtitles-from-existing-subtitles/subtitles/generated/`.
- Verify the first subtitle track is the generated Spanish translation and it is the only default subtitle track. When both formats exist, expect the ASS translation first/default and the TV-safe SRT second/non-default, followed by all original subtitle tracks as non-default.
- Check the player UI for unexpected `[Local]` entries; none should be discoverable from the output root because this workflow does not publish sidecars.
- Read `debug/video-generate-traslated-subtitles-from-existing-subtitles/reports/remux_validation_report.json` and reject the output unless its status is `pass`.

## Output Contract

Return `debug/video-generate-traslated-subtitles-from-existing-subtitles/reports/validation_report.md` with:

- pass/fail status;
- exact failed file paths and timestamps;
- stream metadata summary;
- extracted subtitle samples;
- recommended fixes.

## Acceptance Criteria

- The main agent can decide release readiness from the report.
- Failures are actionable and tied to concrete artifacts.
