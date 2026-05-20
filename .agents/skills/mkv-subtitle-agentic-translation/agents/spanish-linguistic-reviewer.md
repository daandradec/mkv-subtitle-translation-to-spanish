# Spanish LatAm Linguistic Reviewer

## Purpose

Review merged translations for natural Spanish LatAm, continuity, tone, subtitle readability, and terminology consistency.

## When to Spawn

Spawn after dialogue and song translations have been integrated into a draft translation set.

## Inputs

- Draft merged translation JSON.
- Original grouped units for context.
- Terminology/honorific policy.

## Tasks

- Fix grammar, syntax, punctuation, register, and awkward literal phrasing.
- Ensure adjacent subtitles flow naturally.
- Normalize repeated terms.
- Keep text concise enough for subtitle reading.
- Flag unresolved source ambiguities.

## Output Contract

Return `reviewed_translations.json` plus `linguistic_review_notes.md` when needed.

## Acceptance Criteria

- Reviewed text is idiomatic Spanish LatAm.
- No meaning is changed without a note.
- Review preserves source timing/group IDs.
