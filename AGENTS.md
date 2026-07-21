# Repository Guidelines

## Project Structure & Module Organization

This repository contains a Python and PowerShell toolkit for video transcription, subtitle translation, Spanish subtitle normalization, and voice cleanup. Each workflow owns its modules, tests, and canonical PowerShell launcher under `src/<skill-name>/`; reusable code lives under `src/shared/`. The root of `src/` contains only those five project directories. Agent workflows live under `.agents/skills/`. Runtime media goes in `input/`. Every generated artifact goes under deterministic `output/<input-stem>/`: final deliverables at its root, explicitly requested public subtitle exports in `sidecars/`, and helpers/maps/reports in `debug/<skill-name>/`. The MKV translation workflow keeps all generated ASS/SRT files internal under its debug directory and publishes only the final MKV. The bundled voice cleaner model is `models/voice-cleaner/std.rnnn`.

## Build, Test, and Development Commands

- `powershell -ExecutionPolicy Bypass -File .\src\shared\powershell\init_python_env.ps1`: create and validate the local Python 3.12 `.venv`, then install `requirements.txt` and optional WhisperX dependencies.
- `powershell -ExecutionPolicy Bypass -File .\src\shared\powershell\run_tests.ps1`: run the full unit test suite across shared code and all four skills.
- `powershell -ExecutionPolicy Bypass -File .\src\mkv-subtitle-agentic-translation\traducir_subs_mkv.ps1 -InputMkv ".\input\video.mkv"`: run the MKV subtitle translation workflow.
- `powershell -ExecutionPolicy Bypass -File .\src\video-subtitle-agentic-transcription\transcribe_video_audio.ps1 -InputVideo ".\input\video.mkv"`: transcribe video audio and produce a subtitled MKV.
- `powershell -ExecutionPolicy Bypass -File .\src\video-text-agent-transcription\transcribe_video_text.ps1 -InputPath ".\input\video.mkv"`: transcribe video audio into text artifacts.
- `powershell -ExecutionPolicy Bypass -File .\src\video-voice-cleaner\clean_video_voice.ps1 -InputVideo ".\input\video.mkv"`: generate cleaned audio or a cleaned MKV.

External tools must be on `PATH`: `ffmpeg`, `ffprobe`, and `mkvmerge`.

## Coding Style & Naming Conventions

Use Python 3.12-compatible code, four-space indentation, and clear `snake_case` names for modules, functions, variables, and test methods. Keep PowerShell parameters descriptive and PascalCase, matching existing scripts such as `-InputMkv` and `-InputVideo`. Prefer `pathlib.Path` for filesystem logic. Never add random/hash suffixes or a custom workspace-id option. A fresh run must safely clear only the exact direct-child destination `output/<input-stem>/`; translation resume is the explicit preservation exception.

## Testing Guidelines

Tests use the standard library `unittest` framework and live under `src/shared/tests/` or `src/<skill-name>/tests/`. Add focused tests to the owning subproject, especially for path resolution, subtitle text conversion, language detection, normalization, and workspace layout. Use temporary directories for filesystem behavior; do not require real media files in unit tests. Run all test directories through `src/shared/powershell/run_tests.ps1`.

## Commit & Pull Request Guidelines

Recent commits use short imperative summaries, for example `Update README and pending tasks` and `Document dynamic maps and transcription fallback`. Follow that style: one concise subject line describing the change. Pull requests should include purpose, affected workflow, test output, and relevant media/tool assumptions. Include sample output paths when subtitles, MKVs, or reports changed.

## Security & Configuration Tips

Do not commit local videos, generated MKVs, transcripts, or private translation maps unless intentionally curated. Keep `.venv/`, `input/`, and `output/` as local working areas. Do not recreate root `subtitle_work/`, `translations/`, or `tools/` directories. Verify language and subtitle track selection with `ffprobe` or `mkvmerge -J` before running destructive or long workflows.
