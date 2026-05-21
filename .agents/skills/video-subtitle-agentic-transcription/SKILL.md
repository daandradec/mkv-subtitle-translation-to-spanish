---
name: video-subtitle-agentic-transcription
description: "Agentic workflow for video files without embedded subtitles: transcribe original-language speech from local audio with WhisperX when available or openai-whisper fallback, generate SRT/ASS subtitles, convert/remux the source video into a new MKV, and hand the result to mkv-subtitle-agentic-translation."
---

# Video Subtitle Agentic Transcription

## Core Rule

Use this skill when a video needs subtitles created from its audio. Do not translate in this flow. The output is a source-language transcription track embedded in a new MKV suitable for later use by `mkv-subtitle-agentic-translation`.

Always run through the project Python 3.12 virtual environment. The PowerShell flow initializes `.venv/` with `src/init_python_env.ps1`, installs required dependencies from `requirements.txt`, attempts preferred WhisperX dependencies from `requirements-whisperx.txt`, and prepends `.venv/Scripts` to PATH before using `python`, `whisperx`, or `whisper`.

## Agent Lifecycle

Use subagents in small batches and close them after integrating results.

1. Start with `audio-container-inspector`.
2. Run `transcription-runner` only after the audio stream and workspace are known.
3. Run `transcription-reviewer` and `subtitle-postprocessor` after raw SRT/JSON exists.
4. Run `technical-validator` after final SRT/ASS/MKV are generated.
5. Keep at most two active subagents unless the user explicitly requests broader parallel work.

## Required References

- `agents/audio-container-inspector.md`: inspect video streams and select the audio source.
- `agents/transcription-runner.md`: execute WhisperX/openai-whisper locally.
- `agents/transcription-reviewer.md`: review transcript quality and risky segments.
- `agents/subtitle-postprocessor.md`: clean SRT, create ASS, prepare handoff.
- `agents/technical-validator.md`: validate final subtitles and MKV metadata.
- `references/workflow.md`: end-to-end transcription pipeline.
- `references/backends.md`: WhisperX/OpenAI Whisper backend policy.
- `references/formats.md`: SRT/ASS/MKV output contract.
- `references/testing.md`: required validation matrix.

## Workflow

1. Validate the input video:
   - Use `input/` as the canonical folder.
   - If no supported video is available, stop and ask the user to place one video in `input/` or pass an exact path.
   - If multiple videos exist, require exactly one input path.
2. Create a shared workspace id using the same `24 + "-" + 6` rule as the translation workflow.
3. Inspect audio streams with `ffprobe`; choose the user-specified audio index only when the optional `-AudioStreamIndex` parameter is provided. Otherwise choose the default audio stream, falling back to the first audio stream when no default exists.
   - Treat `-AudioStreamIndex` as optional. Use it for multi-audio files when the user wants a non-default track, for example `-AudioStreamIndex 2`.
   - If `-Language` is not provided, derive Whisper/WhisperX language from the selected audio stream metadata (`fre` -> `fr`, `jpn` -> `ja`, `eng` -> `en`, etc.) and pass that language to the backend.
   - If multiple audio streams are marked default, use the first one in container order and tell the user how to override it with `-AudioStreamIndex`.
4. Initialize and activate the local Python 3.12 environment with `src/init_python_env.ps1`.
5. Extract audio to WAV mono 16 kHz in `subtitle_work/<workspace-id>/`.
6. Prefer WhisperX from `.venv/Scripts`. If it is not available after dependency installation, use `openai-whisper` from `.venv/Scripts` and report the fallback.
7. Transcribe with `--task transcribe`; never use translation mode.
8. Postprocess raw SRT/JSON into:
   - `output/<workspace-id>/<stem>.transcribed.srt`;
   - `output/<workspace-id>/<stem>.transcribed.ass`;
   - `subtitle_work/<workspace-id>/transcription_report.json`.
   Keep subtitles readable: max two visible lines per cue, split long cues into sequential cues instead of stacking lines, use WhisperX word timestamps when available, and keep ASS side margins near 10% so text occupies about 80% of video width.
9. Convert/remux the input video into a new MKV with the transcribed SRT embedded as default:
   - `output/<workspace-id>/<stem>.transcribed.mkv`.
10. If the detected language is not supported by `mkv-subtitle-agentic-translation`, warn that transcription succeeded but the translation flow may stop on unsupported language.
11. Validate output subtitle metadata, cue count, and readable samples before reporting completion.

## Guardrails

- Do not install WhisperX globally. Dependencies belong in the project `.venv/`.
- Do not require API keys or external services.
- Do not perform diarization in v1.
- Do not delete raw backend outputs; keep them under `subtitle_work/<workspace-id>/whisper/`.
- Keep generated media and subtitles ignored by Git.
