# Workflow

## 1. Prepare Workspace

- Expect `/input` for source MKV files.
- Write final deliverables to `/output`.
- Use `subtitle_work/` or a temporary folder for extraction, grouping, review, and debug artifacts.
- Never commit media, extracted subtitles, or generated outputs.

## 2. Inspect MKV

- Use `ffprobe` to list streams and metadata.
- Select subtitle streams by language, codec, default flag, and user preference.
- Do not assume English; record detected source language and confidence.

## 3. Extract and Parse Subtitles

- Extract subtitles without recoding when possible.
- Parse with format-aware logic:
  - ASS: split `Dialogue:` into 10 fields and preserve timing/style/effect.
  - SRT/VTT: parse cues structurally.
- Separate visible text from tags/effects.

## 4. Build Semantic Units

- Group adjacent events that form one sentence, sign, or lyric phrase.
- Use punctuation, timing proximity, style, speaker continuity, and line breaks.
- Translation input must be full grouped text, not isolated event fragments.

## 5. Handle Songs Safely

- Detect song styles and karaoke/effect-heavy events.
- Reconstruct full lyric lines from visible text only.
- Reject events containing ASS drawing mode (`\p`) or numeric vector paths.
- For TV-safe output, emit plain text cues instead of per-character effects.
- Omit uncertain intervals rather than producing broken Spanish.

## 6. Translate and Review

- Translate grouped text to Spanish LatAm.
- Keep translations concise enough for subtitle reading speed.
- Run linguistic review after merging dialogue and song translations.

## 7. Generate Outputs

- Produce the subtitle file used for muxing.
- When ASS complexity is high, also produce a TV-safe SRT or plain ASS.
- Remux with `mkvmerge`, not ffmpeg, to avoid poorly interleaved subtitle tracks.
- Set Spanish language metadata and default subtitle flag.

## 8. Validate

- Extract the Spanish subtitle track from the final MKV and inspect samples.
- Confirm readable Spanish near early dialogue and known song timestamps.
- Confirm no visible ASS commands, drawing paths, or numeric garbage.
- Confirm `/output` contains the MKV and subtitle file(s).
