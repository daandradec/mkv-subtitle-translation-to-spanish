# Container Inspector

## Purpose

Inspect the source MKV and identify the subtitle streams, languages, codecs, attachments, chapters, and tool availability needed for the translation workflow.

## When to Spawn

Spawn this subagent before extraction or translation, especially when the source MKV is unknown or has multiple subtitle streams.

## Inputs

- Source MKV path in `/input`.
- Available tool commands or paths for `ffprobe`, `ffmpeg`, and `mkvmerge`.

## Tasks

- Run `ffprobe` or equivalent inspection.
- List video, audio, subtitle, attachment, and chapter streams.
- Detect subtitle languages, codecs, default flags, titles, and durations.
- Recommend the source subtitle stream(s) to process.
- Identify risks such as PGS/image subtitles, missing fonts, multiple editions, or absent language metadata.

## Output Contract

Return `stream_inventory.md` or `stream_inventory.json` with:

- selected source subtitle stream index;
- source language if detectable;
- all subtitle stream candidates and rationale;
- tool availability;
- risks and required user decisions.

## Acceptance Criteria

- The main agent can extract the correct subtitle stream without guessing.
- No translation subagent starts before this inventory exists.
