# PRD: Agentic MKV Subtitle Translation to Spanish LatAm

## Objective

Build a robust workflow that takes one MKV file from `/inputs`, translates its subtitle content to Spanish LatAm through an agentic multi-phase process, and writes the final MKV plus generated subtitle files to `/outputs`.

The workflow must prioritize semantic quality, subtitle timing integrity, and playback compatibility across computers and consumer TVs.

## Current Problem

The first project version translated a specific English ASS subtitle track and muxed it into an MKV. It worked on desktop players after using MKVToolNix, but complex musical subtitle effects produced poor behavior on an LG C4 TV from USB/FAT32: around `00:44:30` to `00:45:49` in `Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.mkv`, song translations rendered as meaningless numbers or effect artifacts instead of Spanish words.

Future versions must avoid translating ASS drawing/effect fragments as text. When the system cannot reconstruct reliable text for a time range, it must omit translation for that interval instead of producing broken subtitles.

## Functional Requirements

1. Input/output layout:
   - `/inputs` contains the source MKV.
   - `/outputs` contains the final translated MKV and the generated subtitle file(s).
   - Intermediate extraction, analysis, and debug artifacts stay outside version control.

2. Agentic translation pipeline:
   - The main agent must coordinate subagents for container inspection, semantic segmentation, dialogue translation, song translation/review, Spanish LatAm linguistic review, and technical validation.
   - Subagents must work from concrete artifacts and return structured results.
   - The main agent integrates outputs, resolves conflicts, runs tests, and produces final files.

3. Translation quality:
   - Detect the subtitle language instead of assuming English.
   - Extract the full visible subtitle text and group it semantically before translation.
   - Avoid translating isolated time fragments when adjacent events complete the same phrase.
   - Translate complete dialogue blocks, signs, and song lyrics into natural Spanish LatAm with correct syntax and semantics.

4. Songs and complex ASS:
   - Reconstruct complete lyric lines before translation.
   - Never translate ASS vector drawing commands, numeric paths, per-character karaoke effects, or style/effect metadata as text.
   - If a song or effect segment cannot be reconstructed confidently, leave that segment untranslated.
   - Prefer TV-safe subtitle output for complex songs and consumer TV playback.

5. Subtitle format strategy:
   - Evaluate whether to preserve ASS, generate simplified ASS, generate SRT, or output multiple subtitle files.
   - Preserve ASS only when styling fidelity matters and the target player supports it.
   - Generate a TV-safe subtitle file when complex ASS effects are detected.
   - The final MKV should use a subtitle format likely to render correctly on common desktop players and TVs.

6. Validation:
   - Unit tests must cover ASS parsing, visible text extraction, semantic grouping, song reconstruction, subtitle generation, and remux command construction.
   - Validation must detect visible ASS commands, numeric drawing paths, empty translated tracks, broken language metadata, and missing default Spanish track.
   - The system must compare extracted final subtitles against expected readable Spanish text before release.

## Non-Goals

- Do not hardcode a single anime release or a single subtitle stream index.
- Do not require uploading large MKV files to Git.
- Do not promise perfect translation for unrecoverable karaoke/effect fragments.

## Success Criteria

- A user can place an MKV in `/inputs`, run the workflow, and receive translated outputs in `/outputs`.
- The Spanish subtitles are semantically coherent because translation happens over grouped text, not isolated fragments.
- Songs either render as readable Spanish lyrics or are intentionally omitted when unsafe.
- Desktop and TV-safe outputs are validated separately.
- Tests prevent regressions like numbers, ASS commands, or drawing paths appearing as translated subtitle text.
