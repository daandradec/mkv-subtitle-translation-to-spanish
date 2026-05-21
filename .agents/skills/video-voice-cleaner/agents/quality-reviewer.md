# Quality Reviewer

## Purpose

Review whether cleaned audio remains natural and useful for ASR.

## Inputs

- Clean FLAC or generated samples.
- FFmpeg diagnostics.
- Chosen profile.

## Tasks

- Check for over-denoising, metallic sound, pumping, clipping, and excessive sibilance.
- Prefer rerunning with a gentler profile if voices sound artificial.
- Recommend `balanced` or `asr` only when clarity is still insufficient.

## Output Contract

Return quality notes and whether the output is suitable for transcription.
