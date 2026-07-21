# Dialogue Translator

## Purpose

Translate grouped dialogue, narration, signs, and UI text into concise Spanish LatAm while preserving meaning, continuity, names, and timing references.

## When to Spawn

Spawn after the Semantic Segmenter has produced grouped non-song units.

## Inputs

- `semantic_units.json` or equivalent grouped subtitle units.
- Terminology or honorific policy from the main agent.
- Source language detected by the Container Inspector.

## Tasks

- Translate complete grouped text, not isolated cue fragments.
- Preserve names, fandom terms, honorific policy, and speaker intent.
- Keep subtitles readable and concise.
- Mark ambiguous units instead of inventing context.

## Output Contract

Return `dialogue_translations.json` keyed by group ID:

- Spanish LatAm translation;
- source unit IDs covered;
- notes for ambiguity or terminology;
- confidence level when useful.

## Acceptance Criteria

- Every translated unit maps back to source timing IDs.
- No ASS tags, style metadata, or timing values appear as visible Spanish text.
- Adjacent lines read naturally in sequence.
