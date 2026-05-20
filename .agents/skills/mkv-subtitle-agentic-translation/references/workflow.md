# Workflow

## 1. Prepare Workspace

- Expect `/input` for source MKV files.
- If `/input` has no MKV files and the user did not provide a valid MKV path, stop before spawning subagents and say: "No se encontró ningún video MKV en la carpeta `input`. Para ejecutar este flujo es obligatorio ubicar un archivo de video `.mkv` con subtítulos incrustados en `input/` o indicar la ruta exacta del archivo."
- If `/input` has multiple MKV files, require exactly one explicit input MKV name/path for the run. Do not choose automatically.
- If the user provides an input name/path, verify it resolves to exactly one existing `.mkv` file before doing any extraction, translation, or remuxing.
- Write final deliverables to `/output`.
- Use `subtitle_work/` or a temporary folder for extraction, grouping, review, and debug artifacts.
- Never commit media, extracted subtitles, or generated outputs.
- Plan subagent usage in small batches before spawning any role. Keep at most two active subagents, wait for results, integrate them, and close completed agents before the next batch.

## 1.1 Agent Lifecycle Checkpoint

- Before spawning a role, confirm whether an existing active subagent is still needed.
- Close completed/stale subagents before creating new ones.
- Launch only roles whose inputs already exist; do not spawn translation/review agents before extraction and segmentation artifacts exist.
- If the session cannot create a new subagent because the limit is reached, free completed agents and retry once. If no slot can be freed, the main agent performs that phase locally and notes the fallback.
- Recommended order: container inspection, then segmentation/song analysis, then dialogue translation/linguistic review, then final technical validation.

## 2. Inspect MKV

- Use `ffprobe` to list streams and metadata.
- Select subtitle streams by language, codec, default flag, and user preference.
- Do not assume English; record detected source language and confidence.
- Validate the detected source language with `src/subtitle_language.py`.
- If the selected MKV has no embedded subtitle streams, stop before processing and say: "No se encontraron subtítulos incrustados en el archivo original para traducir a español."
- Continue only for English, Mandarin Chinese, Hindi, Portuguese, French, Russian, German, Japanese, Wu Chinese/Shanghainese, Korean, or Italian.
- Stop before extraction when the subtitle language is unsupported or the codec is not textual.

## 3. Extract and Parse Subtitles

- Extract subtitles without recoding when possible.
- Parse with format-aware logic:
  - ASS: split `Dialogue:` into 10 fields and preserve timing/style/effect.
  - SRT/VTT: parse cues structurally.
- Convert SRT/VTT/WebVTT input to simple ASS with `src/subtitle_text_to_ass.py` before using ASS-only pipeline stages.
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
- Keep the existing English translation-map workflow unchanged.
- For supported non-English languages, generate local translation maps under `translations/<video_stem>/<source_lang>/`; do not reuse English maps.

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
