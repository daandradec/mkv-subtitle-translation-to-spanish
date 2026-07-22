# Repository Guidelines

## Project Structure & Module Organization

This repository contains a Python, PowerShell, and Bash toolkit for video transcription, subtitle translation, and Spanish subtitle normalization. Each workflow owns its modules, tests, and canonical PowerShell launcher under `src/<skill-name>/`; reusable Python code lives under `src/shared/video_toolkit/`. Repository installation, build, test, cleanup, and shared PowerShell modules live under `scripts/`. Shared and architectural tests live directly under `tests/`; workflow-specific tests remain under `src/<skill-name>/tests/`. Agent workflows live under `.agents/skills/`. Runtime media goes in `inputs/`. Every generated artifact goes under deterministic `outputs/<input-stem>/`: final deliverables at its root, explicitly requested public subtitle exports in `sidecars/`, and helpers/maps/reports in `debug/<skill-name>/`. Strictly ephemeral build, test, log, and processing artifacts stay under `.tmp/`; reusable caches, downloaded models, installation state, and optional Python wheels stay under `.cache/`. `.venv/` is the intentional root-level Python environment.

## Build, Test, and Development Commands

- `powershell -ExecutionPolicy Bypass -File .\scripts\manage_video_toolkit.ps1 setup-python-environment`: create and validate the local Python 3.12 `.venv`, then install `requirements.txt` and optional WhisperX dependencies.
- `bash ./scripts/manage_video_toolkit.sh setup-python-environment`: equivalent environment bootstrap for Ubuntu.
- `powershell -ExecutionPolicy Bypass -File .\scripts\manage_video_toolkit.ps1 run-test-suite`: run the full unit test suite across shared code and all three skills.
- `powershell -ExecutionPolicy Bypass -File .\scripts\manage_video_toolkit.ps1 build-python-package`: optionally build a wheel under `.cache/packages/python/` without leaving root build metadata.
- `powershell -ExecutionPolicy Bypass -File .\scripts\manage_video_toolkit.ps1 clean-temporary-files`: clean only ephemeral artifacts under `.tmp/`.
- `powershell -ExecutionPolicy Bypass -File .\scripts\manage_video_toolkit.ps1 clean-cache-files`: explicitly clear reusable caches, models, installation state, and cached wheels under `.cache/`.
- `powershell -ExecutionPolicy Bypass -File .\src\video-generate-traslated-subtitles-from-existing-subtitles\traducir_subs_mkv.ps1 -InputMkv ".\inputs\video.mkv"`: run the MKV subtitle translation workflow.
- `powershell -ExecutionPolicy Bypass -File .\src\video-generate-new-subtitles-from-audio\transcribe_video_audio.ps1 -InputVideo ".\inputs\video.mkv"`: transcribe video audio and produce a subtitled MKV.
- `powershell -ExecutionPolicy Bypass -File .\src\video-generate-whisper-transcription\transcribe_video_text.ps1 -InputPath ".\inputs\video.mkv"`: transcribe video audio into text artifacts.

External tools must be on `PATH`: `ffmpeg`, `ffprobe`, and `mkvmerge`.

## Coding Style & Naming Conventions

Use Python 3.12-compatible code, four-space indentation, and clear `snake_case` names for modules, functions, variables, and test methods. Keep PowerShell parameters descriptive and PascalCase, matching existing scripts such as `-InputMkv` and `-InputVideo`. Prefer `pathlib.Path` for filesystem logic. Never add random/hash suffixes or a custom workspace-id option. A fresh run must safely clear only the exact direct-child destination `outputs/<input-stem>/`; translation resume is the explicit preservation exception.

## Testing Guidelines

Tests use the standard library `unittest` framework. Shared and architectural tests live directly under `tests/`; workflow-owned tests live under `src/<skill-name>/tests/`. Temporary test workspaces belong only under `.tmp/tests/` and must not contain permanent test source. Add focused tests to the owning location, especially for path resolution, subtitle text conversion, language detection, normalization, and workspace layout. Do not require real media files in unit tests. Run all test directories through `scripts/manage_video_toolkit.ps1 run-test-suite` or `scripts/manage_video_toolkit.sh run-test-suite`.

## Commit & Pull Request Guidelines

Recent commits use short imperative summaries, for example `Update README and pending tasks` and `Document dynamic maps and transcription fallback`. Follow that style: one concise subject line describing the change. Pull requests should include purpose, affected workflow, test output, and relevant media/tool assumptions. Include sample output paths when subtitles, MKVs, or reports changed.

## Security & Configuration Tips

Do not commit local videos, generated MKVs, transcripts, private translation maps, caches, models, or cached wheels unless intentionally curated. Keep `.venv/`, `.tmp/`, `.cache/`, `inputs/`, and `outputs/` as local working areas. Never create root `build/`, `*.egg-info/`, `subtitle_work/`, `translations/`, or `tools/` directories. Reserve any future root `dist/` strictly for user-requested business exports, never for Python packaging or environment setup. Verify language and subtitle track selection with `ffprobe` or `mkvmerge -J` before running destructive or long workflows.
