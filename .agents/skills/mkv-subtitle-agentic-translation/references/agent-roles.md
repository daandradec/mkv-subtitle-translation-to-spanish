# Agent Roles

Use these roles as separate subagents whenever the task is large enough to benefit from parallel work. Each subagent must receive concrete input paths and produce structured artifacts.

Do not create all roles at once. The main agent should run roles in dependency-aware batches, keep no more than two active subagents, wait for each batch to finish, integrate the returned artifact, and close completed subagents before launching later roles.

## Container Inspector

- Inputs: source MKV path, tool availability.
- Tasks: run `ffprobe`, list video/audio/subtitle streams, detect subtitle codecs/languages, identify attachments/fonts, and recommend source subtitle track.
- Output: JSON or markdown summary with selected ffprobe stream index, mkvmerge track id, rationale, subtitle candidates, workspace id, and risks.

## Semantic Segmenter

- Inputs: extracted subtitle file.
- Tasks: parse subtitle format, extract visible text, group adjacent events into complete sentences or semantic blocks, and preserve source event IDs/times.
- Output: grouped units with source IDs, time ranges, original text, style/effect metadata, and grouping confidence.

## Dialogue Translator

- Inputs: grouped non-song dialogue/sign units.
- Tasks: translate to natural Spanish LatAm, preserving names, honorific policy, intent, and subtitle brevity.
- Output: structured translations keyed by group ID, with notes for ambiguous lines.

## Song Translator and Reviewer

- Inputs: grouped song/lyric units and ASS effect metadata.
- Tasks: reconstruct complete lyric lines, reject drawing/effect fragments, translate only reliable lyrics, and mark unsafe intervals as omit.
- Output: translated lyric groups plus omitted intervals and reasons.

## Spanish LatAm Linguistic Reviewer

- Inputs: all translated units.
- Tasks: normalize tone, syntax, punctuation, terminology, and continuity across grouped lines. Build or refine a local term map for names, places, factions, ranks, honorifics, and recurring expressions.
- Output: reviewed translations plus required fixes and glossary/term-map updates.

## Technical Validator

- Inputs: generated subtitle files and final MKV.
- Tasks: validate stream metadata, default flags, extracted final subtitles, timing counts, TV-safe output, and absence of visible ASS commands or numeric path garbage.
- Output: pass/fail report with exact failing timestamps and file paths.

## Main Agent Integration

The main agent integrates all subagent outputs, resolves conflicts, writes final subtitle files, remuxes with `mkvmerge`, runs tests, closes no-longer-needed subagents, and prepares the final user summary. If no subagent slot is available after closing completed agents, the main agent performs the blocked role locally and documents the fallback.
