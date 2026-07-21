---
name: video-generate-traslated-subtitles-from-existing-subtitles
description: Agentic workflow for translating MKV subtitle tracks from any detected source language into Spanish LatAm with semantic grouping, song-lyric reconstruction, TV-safe subtitle output, MKVToolNix remuxing, and technical validation. Use when Codex needs to process MKV subtitles, coordinate subagents for translation/review/QA, create /input and /output subtitle workflows, or avoid ASS karaoke/effect rendering failures on TVs.
---

# Video Generate Traslated Subtitles From Existing Subtitles

## Core Rule

Use subagents. The main agent owns orchestration, integration, tests, and final files. Delegate bounded phases to specialized subagents and require structured artifacts back. Do not translate raw ASS events one-by-one when neighboring events form one sentence or lyric.

Always run project scripts through the local Python 3.12 virtual environment. The canonical launcher `src/video-generate-traslated-subtitles-from-existing-subtitles/traducir_subs_mkv.ps1` initializes `.venv/` via `src/shared/powershell/init_python_env.ps1`, installs `requirements.txt` and preferred WhisperX requirements when needed, and uses `.venv/Scripts/python.exe` for every Python module.

## Agent Lifecycle

Treat subagents as a limited resource. Do not spawn every role at once.

Use this lifecycle for each phase:

1. Start with the minimum blocking subagent, usually `container-inspector`.
2. Wait for its structured result before launching dependent roles.
3. Close completed subagents immediately after integrating their result.
4. Keep at most two active subagents at the same time unless the user explicitly asks for broad parallel work.
5. If agent creation fails because the session limit is reached, close completed or stale subagents, then retry the needed role. If no slot can be freed, perform that phase locally and record that fallback in the final summary.

Recommended batches:

- Batch 1: `container-inspector`.
- Batch 2: `semantic-segmenter` plus `song-translator-reviewer` only after extraction/parsing exists.
- Batch 3: `dialogue-translator` plus `spanish-linguistic-reviewer` when translation artifacts are ready.
- Batch 4: `technical-validator` after final subtitle files and MKV are generated.

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

1. Validate the source MKV before starting the workflow:
   - The canonical input folder is `input/`, not `inputs/`. If the user writes `inputs/<name>.mkv` but `input/<name>.mkv` exists, use `input/<name>.mkv` and mention the correction.
   - If `/input` has no MKV files and the user did not provide a valid MKV path, stop immediately and say: "No se encontró ningún video MKV en la carpeta `input`. Para ejecutar este flujo es obligatorio ubicar un archivo de video `.mkv` con subtítulos incrustados en `input/` o indicar la ruta exacta del archivo."
   - If `/input` has multiple MKV files, do not choose one automatically. The workflow can process only one video per run, so require exactly one input MKV path/name and verify that it exists.
   - If an input name/path is provided, verify that it resolves to one existing `.mkv` file before spawning subagents.
   - The user may optionally provide a subtitle stream index. Pass it to `src/video-generate-traslated-subtitles-from-existing-subtitles/traducir_subs_mkv.ps1` as `-SourceSubtitleStreamIndex <ffprobe-index>` and use that exact track as the source.
2. Initialize the local Python 3.12 environment before running Python helpers. If Python 3.12 is missing, stop and tell the user to install it before continuing.
3. Use one deterministic per-video output directory: `output/<stem>/`, where `<stem>` is the complete input filename without its extension. Never append a hash, random suffix, or custom workspace id.
   - A fresh run safely clears the existing contents of that exact directory before writing new artifacts.
   - `-Resume` is the only mode that preserves an existing translation checkpoint and maps.
   - Write workflow helpers only under `output/<stem>/debug/video-generate-traslated-subtitles-from-existing-subtitles/`.
4. Keep only the final MKV deliverable in `output/<stem>/`. Store source, translated, and TV-safe subtitle files under `output/<stem>/debug/video-generate-traslated-subtitles-from-existing-subtitles/subtitles/`; store reports, maps, checkpoints, and every other helper under the appropriate skill debug subdirectory. Do not publish ASS/SRT sidecars for this workflow.
5. Spawn subagents in lifecycle-controlled batches. Wait for each batch, integrate its artifacts, and close completed agents before creating the next batch.
6. Validate that the input MKV has embedded text subtitles and a supported source language with `video_generate_traslated_subtitles_from_existing_subtitles.subtitle_language`, whose implementation lives under `src/video-generate-traslated-subtitles-from-existing-subtitles/python/`. If no subtitles are found, stop immediately and tell the user: "No se encontraron subtítulos incrustados en el archivo original, por lo que este flujo no puede traducirlo a español. Cuando quieras crear subtítulos desde el audio del video, usa la skill `video-generate-new-subtitles-from-audio`, que estará orientada a transcribir las voces y generar un MKV con subtítulos base para un flujo posterior de traducción."
   Continue only for English, Mandarin Chinese, Hindi, Portuguese, French, Russian, German, Japanese, Wu Chinese/Shanghainese, Korean, or Italian.
   - If the user provided `-SourceSubtitleStreamIndex`, use that exact subtitle stream after validating that it is textual and language-supported.
   - If no subtitle stream index is provided, use the default embedded subtitle track when it is textual and language-supported.
   - If there is no usable default subtitle track, do not blindly use the first one. Prefer complete text tracks over `Forced`, prefer non-CC over CC unless requested, prefer larger event coverage/duration, and prefer the likely original/source-language track when metadata makes it clear.
   - Report the selected `ffprobe` stream index and mkvmerge track id.
7. Extract subtitle streams with `ffmpeg`/`ffprobe`; remux final MKV with `mkvmerge`.
   - ASS input can enter the pipeline directly.
   - SRT/VTT/WebVTT input must be converted with the shared `video_toolkit.subtitles.text` module before ASS-oriented processing.
   - Image subtitles such as PGS are not supported.
   - The canonical launcher extracts the selected source subtitle before resolving translation maps.
   - When maps are missing, it writes `output/<stem>/debug/video-generate-traslated-subtitles-from-existing-subtitles/checkpoints/translation_checkpoint.json`, writes a matching `README.txt` under the language map directory, and stops with `[CHECKPOINT:AWAITING_TRANSLATION_MAPS]`.
   - This checkpoint is not a final workflow result. Read the extracted source path from it, run the segmentation/translation/review agents, write the maps to the recorded directory, and execute the recorded resume command with the same workspace and track IDs.
8. Build a full text model before translation:
   - parse ASS/SRT/VTT structurally;
   - strip non-visible tags safely;
   - group adjacent subtitle events into semantic units;
   - reconstruct complete song lyric lines before translating.
9. Translate grouped units into Spanish LatAm and preserve timing references.
   - Resolve or generate translation maps under `output/<stem>/debug/video-generate-traslated-subtitles-from-existing-subtitles/translations/<source_lang>/` for every supported source language, including English.
   - Do not rely on legacy root-level maps. If old maps exist, migrate or copy them into the deterministic debug directory and validate that they belong to the same source subtitles before using them.
   - Never reuse maps from a different language or unrelated video.
   - Maintain a local glossary/term map for names, places, factions, ranks, and recurring terms. Apply it before final subtitle generation so ASS and SRT use consistent Spanish/transliterated names.
10. For complex ASS song/effect segments, prefer a plain TV-safe subtitle line. If text cannot be reconstructed confidently, omit translation for those intervals.
11. Generate the translated MKV in `output/<stem>/`. Keep the subtitle files used for muxing and the optional TV-safe variant under `output/<stem>/debug/video-generate-traslated-subtitles-from-existing-subtitles/subtitles/generated/`.
12. Remux so every original subtitle track is preserved but marked non-default. When both Spanish variants are embedded, order `Español LatAm` ASS first among subtitle tracks and mark it as the only default; keep `Español LatAm TV-safe` immediately after it as a non-default fallback. When only one Spanish format is embedded, make that track first and default.
13. Validate the remuxed track order/default flags and persist `debug/video-generate-traslated-subtitles-from-existing-subtitles/reports/remux_validation_report.json`; fail the workflow if the generated Spanish track is not first and uniquely default.
14. Run tests and validations before declaring success.

## Guardrails

- Never translate ASS drawing commands such as `m`, `l`, `b` path data or events containing `\p` as lyrics.
- Never expose ASS override tags, numeric paths, or karaoke timing commands as visible Spanish text.
- Do not mark a Spanish track as valid only because it exists; extract it from the final MKV and confirm readable Spanish appears near known timestamps.
- Preserve honorifics only when requested or fandom context strongly benefits.
- Keep generated media, extracted subtitles, and debug artifacts out of Git.
- Stop early when the detected source subtitle language is unsupported, and show the supported-language list.
