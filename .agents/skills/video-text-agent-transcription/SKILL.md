---
name: video-text-agent-transcription
description: Agentic workflow for detecting and confirming spoken language, then transcribing one video or a folder into native WhisperX/Whisper outputs plus clean RAG-ready Markdown. Use when Codex needs high-quality text transcripts from video/audio files, batch text transcription from input/, language-confirmed WhisperX transcription, Markdown knowledge-base preparation, Whisper fallback, or transcript cleanup without creating MKV subtitles.
---

# Video Text Agent Transcription

## Core Workflow

Use this skill to create text transcripts, not subtitle MKVs. Keep it independent from `video-subtitle-agentic-transcription`.

1. Inspect the requested input. Accept a single video file or a folder. If no path is provided, use `input/` only when it contains exactly one valid video with audio.
2. Initialize the project `.venv`, then establish the spoken language before the definitive transcription:
   - If the user already supplied a language, treat it as proposed but still ask for confirmation.
   - Otherwise run `scripts/detect_language.py` for each input using the same Whisper model/device planned for transcription.
   - Read `references/whisper-languages.md`, show the detected/proposed code and Spanish name, then provide the complete available-language list.
   - Ask: `¿Es correcto? Responde “sí” para confirmarlo o indica otro código/nombre.`
   - Stop and wait for the answer. Skip this pause only when the user explicitly says the language is already confirmed or requests non-interactive execution.
   - For folders, show one compact detection table and ask once for all confirmations/corrections.
3. Convert the confirmed name to its Whisper code and always pass it through `-Language`; never leave final transcription on autodetection after confirmation.
4. Coordinate subagents only when useful and keep their lifecycle bounded: inspector, transcription runner, transcript editor, Markdown formatter, and validator. Reuse or wait for agents if the session has an active-agent limit.
5. Run the deterministic script:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\transcribe_video_text.ps1 -InputPath "<path>"
```

6. For batch folder input, let the script process videos non-recursively and continue after individual failures.
7. Validate that each successful video has a unique `output/<workspace-id>/` folder with native backend files and `<videoname>.md`.

Language probe command:

```powershell
.\.venv\Scripts\python.exe `
  .\.agents\skills\video-text-agent-transcription\scripts\detect_language.py `
  --input ".\input\video.mp4" `
  --model large-v3 `
  --device cuda `
  --compute-type float16 `
  --json
```

Treat confidence below `0.60` or disagreement among samples as uncertain, but always let the user decide. Do not infer a correction from filenames or metadata alone.

## Parameters

Prefer defaults unless the user asks for a specific tradeoff:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\transcribe_video_text.ps1 `
  -InputPath ".\input\video.mp4" `
  -Backend auto `
  -WhisperXModel large-v3 `
  -WhisperModel turbo `
  -Device cuda `
  -ComputeType float16 `
  -BatchSize 8
```

For maximum WhisperX decoding quality with literal outputs, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\transcribe_video_text.ps1 `
  -InputPath ".\input\video.mp4" `
  -Language es `
  -WhisperXQuality maximum `
  -WhisperXInitialPrompt "Short domain context" `
  -WhisperXHotwords "rare name, technical term" `
  -Verbatim
```

- `-InputPath`: file or folder. Folder mode processes all valid videos in name order.
- `-Language`: required after the confirmation step. Pass the confirmed Whisper code, such as `es`, `en`, `de`, or `fr`.
- `-WhisperXQuality`: `balanced` uses beam 5/patience 1; `maximum` uses beam 10/patience 2.
- `-WhisperXInitialPrompt` and `-WhisperXHotwords`: optional, curated context and vocabulary; do not derive them blindly from a noisy transcript.
- `-Verbatim`: preserve recognized words, repetitions, fillers, and noise labels while only repairing encoding and whitespace.
- `-AudioStreamIndex`: optional. `-1` means audio default, then first audio.
- `-WorkspaceId`: optional and only for a single video.
- `-Force`: only when intentionally reusing a provided workspace.
- `-DryRun`: inspect planned commands without transcribing.

## Output Contract

For each processed video, expect:

```text
output/<workspace-id>/<videoname>.json
output/<workspace-id>/<videoname>.srt
output/<workspace-id>/<videoname>.vtt
output/<workspace-id>/<videoname>.txt
output/<workspace-id>/<videoname>.tsv
output/<workspace-id>/<videoname>.md
output/<workspace-id>/text_transcription_report.json
```

JSON/TSV stay close to backend output. SRT, VTT, TXT, Markdown, and report are required for a successful run and should contain postprocessed clean text.

## Quality Rules

- Preserve the original spoken language; do not translate.
- Optimize Markdown for knowledge retrieval: use one time-ranged heading per paragraph, readable paragraphs, and clean UTF-8.
- Apply the same conservative text cleanup to canonical SRT, VTT, and TXT outputs.
- Remove nonverbal noise, empty greetings, excessive filler, repeated boilerplate, sponsorship-like clutter, and duplicate fragments.
- Treat backend language detection as a hint, not absolute truth; trust the postprocess report when text evidence corrects a mismatch.
- Preserve concepts, methods, examples, design decisions, best practices, domain vocabulary, and any substantive topic.
- Do not edit generated files manually unless the user explicitly asks for a repair. Prefer improving the script or rerunning the flow.

## References

- Read `references/workflow.md` for the full operational sequence.
- Read `references/backends.md` when adjusting WhisperX/Whisper behavior.
- Read `references/whisper-languages.md` before presenting the language-confirmation question.
- Read `references/markdown-format.md` when changing Markdown structure or cleanup rules.
- Read `references/testing.md` before modifying scripts or validation.
