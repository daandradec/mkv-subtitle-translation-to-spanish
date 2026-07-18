---
name: video-text-agent-transcription
description: Agentic workflow for transcribing one video or a folder of videos into native WhisperX/Whisper outputs plus clean RAG-ready Markdown. Use when Codex needs high-quality text transcripts from video/audio files, batch text transcription from input/, Markdown knowledge-base preparation, WhisperX with Whisper fallback, or transcript cleanup without creating MKV subtitles.
---

# Video Text Agent Transcription

## Core Workflow

Use this skill to create text transcripts, not subtitle MKVs. Keep it independent from `video-subtitle-agentic-transcription`.

1. Inspect the requested input. Accept a single video file or a folder. If no path is provided, use `input/` only when it contains exactly one valid video with audio.
2. Coordinate subagents only when useful and keep their lifecycle bounded: inspector, transcription runner, transcript editor, Markdown formatter, and validator. Reuse or wait for agents if the session has an active-agent limit.
3. Run the deterministic script:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\transcribe_video_text.ps1 -InputPath "<path>"
```

4. For batch folder input, let the script process videos non-recursively and continue after individual failures.
5. Validate that each successful video has a unique `output/<workspace-id>/` folder with native backend files and `<videoname>.md`.

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

- `-InputPath`: file or folder. Folder mode processes all valid videos in name order.
- `-Language`: optional. Leave empty for WhisperX/Whisper autodetection; pass a code/name only when the user requests it.
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
- Read `references/markdown-format.md` when changing Markdown structure or cleanup rules.
- Read `references/testing.md` before modifying scripts or validation.
