# Workflow

## 1. Prepare Workspace

- Expect `/input` for source MKV files.
- Treat `input/` as the only canonical input folder. If the user says `inputs/<file>.mkv`, correct it to `input/<file>.mkv` only when that file exists.
- If `/input` has no MKV files and the user did not provide a valid MKV path, stop before spawning subagents and say: "No se encontró ningún video MKV en la carpeta `input`. Para ejecutar este flujo es obligatorio ubicar un archivo de video `.mkv` con subtítulos incrustados en `input/` o indicar la ruta exacta del archivo."
- If `/input` has multiple MKV files, require exactly one explicit input MKV name/path for the run. Do not choose automatically.
- If the user provides an input name/path, verify it resolves to exactly one existing `.mkv` file before doing any extraction, translation, or remuxing.
- Use the exact source filename without its extension as `<stem>`; never add a random/hash suffix or accept a custom workspace id.
- Write only the final MKV deliverable to `output/<stem>/`; do not publish ASS/SRT sidecars for this workflow.
- Write source subtitles under `output/<stem>/debug/video-generate-traslated-subtitles-from-existing-subtitles/subtitles/source/` and generated ASS/SRT files under `output/<stem>/debug/video-generate-traslated-subtitles-from-existing-subtitles/subtitles/generated/`.
- Write grouping, review, translation maps, checkpoints, postprocessing artifacts, and reports under their appropriate subdirectories in `output/<stem>/debug/video-generate-traslated-subtitles-from-existing-subtitles/`.
- A fresh run clears the existing contents of `output/<stem>/` after validating that it is a direct child of `output/` and contains no reparse points. Use `-Resume` to preserve an existing translation checkpoint and its maps.
- Never commit media, extracted subtitles, or generated outputs.
- Initialize `.venv/` with Python 3.12 using `src/shared/powershell/init_python_env.ps1` before running Python helpers. Use `.venv/Scripts/python.exe`, not the global Python.
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
- If the user provides a subtitle stream index, pass it as `-SourceSubtitleStreamIndex <ffprobe-index>` and use that exact textual, language-supported stream.
- When no exact stream is provided, use the default embedded subtitle track when it is textual and language-supported.
- If there is no usable default subtitle track, inspect all subtitle candidates. Exclude `Forced` tracks when complete tracks exist, avoid CC/SDH unless requested, prefer higher event coverage/duration, and prefer the likely original/source-language track when metadata supports it.
- Do not assume English; record detected source language and confidence.
- Validate the detected source language with `video_generate_traslated_subtitles_from_existing_subtitles.subtitle_language` from `src/video-generate-traslated-subtitles-from-existing-subtitles/python/`.
- If the selected MKV has no embedded subtitle streams, stop before processing and say: "No se encontraron subtítulos incrustados en el archivo original, por lo que este flujo no puede traducirlo a español. Cuando quieras crear subtítulos desde el audio del video, usa la skill `video-generate-new-subtitles-from-audio`, que estará orientada a transcribir las voces y generar un MKV con subtítulos base para un flujo posterior de traducción."
- Continue only for English, Mandarin Chinese, Hindi, Portuguese, French, Russian, German, Japanese, Wu Chinese/Shanghainese, Korean, or Italian.
- Stop before extraction when the subtitle language is unsupported or the codec is not textual.

## 3. Extract and Parse Subtitles

- Extract subtitles without recoding when possible.
- The canonical launcher performs this extraction before checking for translation maps.
- If maps are absent, treat `[CHECKPOINT:AWAITING_TRANSLATION_MAPS]` as a required agent handoff, not as completion or a broken import.
- Read `output/<stem>/debug/video-generate-traslated-subtitles-from-existing-subtitles/checkpoints/translation_checkpoint.json`; it records the exact source ASS, language, stream/track IDs, map directory, and resume command.
- Generate maps from that extracted subtitle and run the recorded command with `-Resume`, `SourceSubtitleStreamIndex`, and `SourceMkvTrackId`.
- Parse with format-aware logic:
  - ASS: split `Dialogue:` into 10 fields and preserve timing/style/effect.
  - SRT/VTT: parse cues structurally.
- Convert SRT/VTT/WebVTT input to simple ASS with the shared `video_toolkit.subtitles.text` module before using ASS-only pipeline stages.
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
- Resolve or generate local translation maps under `output/<stem>/debug/video-generate-traslated-subtitles-from-existing-subtitles/translations/<source_lang>/` for every supported language, including English.
- Do not rely on legacy root-level maps. Migrate only maps verified against the same extracted source subtitle.
- Do not reuse maps across different source languages or unrelated videos.
- Maintain and apply a local term map/glossary for recurring names, places, factions, ranks, and culturally specific terms.

## 7. Generate Outputs

- Produce the subtitle file used for muxing.
- When ASS complexity is high, also produce a TV-safe SRT or plain ASS.
- Remux with `mkvmerge`, not ffmpeg, to avoid poorly interleaved subtitle tracks.
- Preserve original subtitle tracks but mark all of them non-default. Put the generated Spanish track first among subtitle tracks. When both formats are embedded, make `Español LatAm` ASS the only default and place the non-default `Español LatAm TV-safe` SRT immediately after it. When only one format is embedded, make that Spanish track first and default.

## 8. Validate

- Extract the Spanish subtitle track from the final MKV and inspect samples.
- Confirm readable Spanish near early dialogue and known song timestamps.
- Confirm no visible ASS commands, drawing paths, or numeric garbage.
- Confirm the final MKV is the only file at the root of `output/<stem>/`, generated ASS/SRT files are under `debug/video-generate-traslated-subtitles-from-existing-subtitles/subtitles/generated/`, and no external subtitle can appear as a `[Local]` player track.
- Confirm the first subtitle track is Spanish, only the intended Spanish track has `default=1`, and every original subtitle track has `default=0`.
- Persist the machine-readable result at `debug/video-generate-traslated-subtitles-from-existing-subtitles/reports/remux_validation_report.json` and fail the workflow when the order/default contract is not met.
