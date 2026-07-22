# Testing

## Unit Tests

- Workspace id and output paths.
- Backend selection:
  - WhisperX preferred;
  - Whisper fallback warning;
  - clear error if no backend exists.
- Postprocess:
  - rejects missing/empty SRT;
  - writes the clean SRT under the internal postprocess workspace;
  - does not generate ASS by default;
  - writes language metadata and translation warning.
- Remux:
  - selects native `mkvmerge` for Matroska/WebM;
  - selects one-pass FFmpeg shared-timeline remux for MP4/MOV and other containers;
  - never adds `-ss` or a fixed subtitle delay;
  - preserves source stream counts and adds exactly one subtitle stream;
  - confirms every embedded cue receives the same timestamp transformation within 5 ms.
- Sidecars:
  - default output has no same-stem SRT/ASS beside the MKV;
  - `--export-ass-file-subtitles` extracts from the embedded track rather than the pre-remux SRT;
  - exported ASS cue count and first cue match the normalized embedded timeline;
  - optional ASS is written under `outputs/<stem>/sidecars/`.

## Script Checks

- Parse `scripts/manage_video_toolkit.ps1` and its `setup-python-environment` command.
- Parse `src/video-generate-new-subtitles-from-audio/transcribe_video_audio.ps1`.
- Compile all Python sources under `src/shared/video_toolkit/` and `src/video-generate-new-subtitles-from-audio/python/`.
- Validate that missing Python 3.12 fails with a clear installation message.
- Use `-DryRun` to inspect backend command without transcription.

## Manual Validation

- Run against a short MKV and a short MP4 without subtitles.
- Run the generated MP4 edit-list regression fixture and compare the first audible sample with the first embedded cue before and after remuxing.
- Confirm generated MKV includes a default transcribed subtitle track.
- Confirm the player lists no `[Local]` subtitle track in the default mode.
- Run once with `--export-ass-file-subtitles` and verify the separate ASS starts at the same instant as the embedded track.
- Open or extract the embedded SRT and sample readable text.
- Pass the generated MKV to `video-generate-traslated-subtitles-from-existing-subtitles` when the detected language is supported.
