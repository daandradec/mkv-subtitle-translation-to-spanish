# Audio Container Inspector

## Purpose

Inspect the source MKV, identify audio streams, and choose the stream to transcribe.

## Inputs

- Source MKV path.
- Optional requested audio stream index.

## Tasks

- Use `ffprobe` to list video, audio, subtitle, and attachment streams.
- Report audio stream index, language metadata, title, channel layout, codec, and default flag.
- Select exactly one audio stream: requested index first, otherwise default audio, otherwise first audio.
- Warn if the MKV already has subtitles; transcription can still proceed, but the user may prefer translation.
- Stop if no audio streams exist.

## Output Contract

Return a short markdown or JSON report with selected ffprobe audio index, rationale, detected audio metadata, and risks.
