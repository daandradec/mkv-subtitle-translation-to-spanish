# Audio Container Inspector

## Purpose

Inspect the source video, identify audio streams, and choose the stream to transcribe.

## Inputs

- Source video path.
- Optional requested audio stream index.

## Tasks

- Use `ffprobe` to list video, audio, subtitle, and attachment streams when present.
- Report audio stream index, language metadata, title, channel layout, codec, and default flag.
- Select exactly one audio stream: optional requested index first, otherwise default audio, otherwise first audio.
- When no language is passed explicitly, derive the transcription language from the selected audio stream metadata and report the backend language code to use.
- If more than one audio stream is marked default, choose the first one in container order and state that the user can override it with `-AudioStreamIndex`.
- Warn if the source video already has subtitles; transcription can still proceed, but the user may prefer translation when the subtitles are embedded in an MKV.
- Stop if no audio streams exist.

## Output Contract

Return a short markdown or JSON report with selected ffprobe audio index, rationale, detected audio metadata, and risks.
