# Audio Container Inspector

## Purpose

Inspect the source video, identify audio streams, and choose the stream to clean.

## Inputs

- Source video path.
- Optional requested audio stream index.

## Tasks

- Use `ffprobe` to list video, audio, subtitle, and attachment streams when present.
- Report audio stream index, language metadata, title, codec, channel layout, sample rate, and default flag.
- Select exactly one audio stream: optional requested index first, otherwise default audio, otherwise first audio.
- Warn when multiple audio streams are marked default and document how to override with `-AudioStreamIndex`.
- Stop if no audio streams exist.

## Output Contract

Return selected audio index, rationale, metadata, and risks.
