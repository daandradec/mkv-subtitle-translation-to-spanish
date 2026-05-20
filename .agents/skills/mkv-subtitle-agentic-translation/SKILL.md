---
name: mkv-subtitle-agentic-translation
description: Agentic workflow for translating MKV subtitle tracks from any detected source language into Spanish LatAm with semantic grouping, song-lyric reconstruction, TV-safe subtitle output, MKVToolNix remuxing, and technical validation. Use when Codex needs to process MKV subtitles, coordinate subagents for translation/review/QA, create /input and /output subtitle workflows, or avoid ASS karaoke/effect rendering failures on TVs.
---

# MKV Subtitle Agentic Translation

## Core Rule

Use subagents. The main agent owns orchestration, integration, tests, and final files. Delegate bounded phases to specialized subagents and require structured artifacts back. Do not translate raw ASS events one-by-one when neighboring events form one sentence or lyric.

## Required References

Read only the references needed for the current task:

- `agents/container-inspector.md`: inspect MKV streams and source subtitle candidates.
- `agents/semantic-segmenter.md`: group subtitle events into complete semantic units.
- `agents/dialogue-translator.md`: translate dialogue/sign units into Spanish LatAm.
- `agents/song-translator-reviewer.md`: reconstruct and translate safe song lyrics.
- `agents/spanish-linguistic-reviewer.md`: review merged Spanish for naturalness and consistency.
- `agents/technical-validator.md`: validate final subtitle files and remuxed MKV.
- `references/agent-roles.md`: subagent responsibilities and output contracts.
- `references/workflow.md`: end-to-end pipeline and required checkpoints.
- `references/subtitle-formats.md`: ASS/SRT/TV-safe decisions.
- `references/testing.md`: unit, fixture, and manual validation matrix.

## Workflow

1. Inspect `/input` and select the MKV source. If multiple MKVs exist, ask the user which one to process.
2. Create `/output` for final deliverables and use `subtitle_work/` or a temp workspace for intermediates.
3. Spawn subagents for inspection, segmentation, translation, song handling, linguistic review, and technical validation. Keep write scopes disjoint.
4. Extract subtitle streams with `ffmpeg`/`ffprobe`; remux final MKV with `mkvmerge`.
5. Build a full text model before translation:
   - parse ASS/SRT/VTT structurally;
   - strip non-visible tags safely;
   - group adjacent subtitle events into semantic units;
   - reconstruct complete song lyric lines before translating.
6. Translate grouped units into Spanish LatAm and preserve timing references.
7. For complex ASS song/effect segments, prefer a plain TV-safe subtitle line. If text cannot be reconstructed confidently, omit translation for those intervals.
8. Generate outputs in `/output`:
   - translated MKV;
   - final subtitle file used for muxing;
   - optional TV-safe subtitle file when ASS complexity is detected.
9. Run tests and validations before declaring success.

## Guardrails

- Never translate ASS drawing commands such as `m`, `l`, `b` path data or events containing `\p` as lyrics.
- Never expose ASS override tags, numeric paths, or karaoke timing commands as visible Spanish text.
- Do not mark a Spanish track as valid only because it exists; extract it from the final MKV and confirm readable Spanish appears near known timestamps.
- Preserve honorifics only when requested or fandom context strongly benefits.
- Keep generated media, extracted subtitles, and debug artifacts out of Git.
