---
name: mkv-subtitle-agentic-translation
description: Agentic workflow for translating MKV subtitle tracks from any detected source language into Spanish LatAm with semantic grouping, song-lyric reconstruction, TV-safe subtitle output, MKVToolNix remuxing, and technical validation. Use when Codex needs to process MKV subtitles, coordinate subagents for translation/review/QA, create /input and /output subtitle workflows, or avoid ASS karaoke/effect rendering failures on TVs.
---

# MKV Subtitle Agentic Translation

## Core Rule

Use subagents. The main agent owns orchestration, integration, tests, and final files. Delegate bounded phases to specialized subagents and require structured artifacts back. Do not translate raw ASS events one-by-one when neighboring events form one sentence or lyric.

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
   - If `/input` has no MKV files and the user did not provide a valid MKV path, stop immediately and say: "No se encontró ningún video MKV en la carpeta `input`. Para ejecutar este flujo es obligatorio ubicar un archivo de video `.mkv` con subtítulos incrustados en `input/` o indicar la ruta exacta del archivo."
   - If `/input` has multiple MKV files, do not choose one automatically. The workflow can process only one video per run, so require exactly one input MKV path/name and verify that it exists.
   - If an input name/path is provided, verify that it resolves to one existing `.mkv` file before spawning subagents.
2. Create `/output` for final deliverables and use `subtitle_work/` or a temp workspace for intermediates.
3. Spawn subagents in lifecycle-controlled batches. Wait for each batch, integrate its artifacts, and close completed agents before creating the next batch.
4. Validate that the input MKV has embedded text subtitles and a supported source language with `src/subtitle_language.py`. If no subtitles are found, stop immediately and tell the user: "No se encontraron subtítulos incrustados en el archivo original para traducir a español."
   Continue only for English, Mandarin Chinese, Hindi, Portuguese, French, Russian, German, Japanese, Wu Chinese/Shanghainese, Korean, or Italian.
5. Extract subtitle streams with `ffmpeg`/`ffprobe`; remux final MKV with `mkvmerge`.
   - ASS input can enter the pipeline directly.
   - SRT/VTT/WebVTT input must be converted with `src/subtitle_text_to_ass.py` before ASS-oriented processing.
   - Image subtitles such as PGS are not supported.
6. Build a full text model before translation:
   - parse ASS/SRT/VTT structurally;
   - strip non-visible tags safely;
   - group adjacent subtitle events into semantic units;
   - reconstruct complete song lyric lines before translating.
7. Translate grouped units into Spanish LatAm and preserve timing references.
   - Keep the existing English-map workflow unchanged for English.
   - For supported non-English sources, generate local maps under `translations/<video_stem>/<source_lang>/` and pass them to `src/traducir_subs_mkv.ps1` with `-TranslationJson`.
   - Never reuse English maps for non-English sources.
8. For complex ASS song/effect segments, prefer a plain TV-safe subtitle line. If text cannot be reconstructed confidently, omit translation for those intervals.
9. Generate outputs in `/output`:
   - translated MKV;
   - final subtitle file used for muxing;
   - optional TV-safe subtitle file when ASS complexity is detected.
10. Run tests and validations before declaring success.

## Guardrails

- Never translate ASS drawing commands such as `m`, `l`, `b` path data or events containing `\p` as lyrics.
- Never expose ASS override tags, numeric paths, or karaoke timing commands as visible Spanish text.
- Do not mark a Spanish track as valid only because it exists; extract it from the final MKV and confirm readable Spanish appears near known timestamps.
- Preserve honorifics only when requested or fandom context strongly benefits.
- Keep generated media, extracted subtitles, and debug artifacts out of Git.
- Stop early when the detected source subtitle language is unsupported, and show the supported-language list.
