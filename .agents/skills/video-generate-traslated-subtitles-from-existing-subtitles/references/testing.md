# Testing and Validation

## Unit Tests

Create tests for:

- ASS dialogue parsing into exactly 10 fields.
- Visible text extraction without ASS override tags.
- Rejection of drawing-mode events and numeric vector paths.
- Semantic grouping across adjacent subtitle events.
- Song lyric reconstruction from safe visible text.
- Omission behavior for unsafe or low-confidence song intervals.
- Generation of plain TV-safe cues.
- Remux command construction with `mkvmerge`.

## Fixtures

Include small synthetic fixtures rather than real copyrighted subtitles:

- Normal dialogue split across two cues.
- A complete sentence across multiple adjacent ASS events.
- Karaoke per-character events.
- ASS drawing event with `\p`.
- Song segment that should be omitted.
- Song segment that should become one readable Spanish cue.

## Integration Checks

For generated MKV files:

- `ffprobe` shows Spanish subtitle language `spa`.
- The generated Spanish subtitle is the first subtitle track and the only default track.
- With both formats, translated ASS precedes the non-default TV-safe SRT, and both precede every original subtitle track.
- Extracted Spanish subtitle track contains readable Spanish.
- No generated visible line matches ASS command patterns or long numeric paths.
- Known song timestamps do not render garbage text.
- The output root contains only the final MKV as a file; generated ASS/SRT helpers remain under `debug/video-generate-traslated-subtitles-from-existing-subtitles/subtitles/`.

## Manual QA

Check at least:

- First dialogue minute.
- A mid-movie dialogue scene.
- A sign-heavy scene.
- A song/lyric section.
- Final credits or ending song.

When TV compatibility is a target, test the TV-safe file on the target device class if possible.
