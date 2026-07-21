# Semantic Segmenter

## Purpose

Parse subtitle files structurally and group adjacent events into complete semantic units before translation.

## When to Spawn

Spawn immediately after subtitle extraction and before any translation work.

## Inputs

- Extracted subtitle file path.
- Subtitle codec/format from the Container Inspector.

## Tasks

- Parse ASS, SRT, or VTT with format-aware logic.
- Extract visible text without destroying timing/style references.
- Group adjacent events that complete one sentence, sign, thought, or lyric.
- Preserve event IDs, time ranges, style, effect, and confidence metadata.
- Classify units as dialogue, sign, song, credit, unsafe effect, or unknown.

## Output Contract

Return `semantic_units.json` with:

- group ID;
- source event IDs;
- start/end time range;
- original visible text;
- classification;
- style/effect metadata;
- grouping confidence.

## Acceptance Criteria

- Translation input contains complete semantic text whenever possible.
- Per-character karaoke, drawing commands, and numeric paths are not classified as normal dialogue.
