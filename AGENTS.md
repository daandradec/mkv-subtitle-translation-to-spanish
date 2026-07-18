# Repository Guidelines

## Project Structure & Module Organization

This repository contains a Python and PowerShell toolkit for video transcription, subtitle translation, Spanish subtitle normalization, and voice cleanup. Core modules, tests, and `.ps1` orchestration scripts live in `src/`. Agent workflows live under `.agents/skills/`. Runtime media goes in `input/`, intermediate files in `subtitle_work/`, translation JSON maps in `translations/`, and final MKV/SRT/ASS outputs in `output/`. The bundled voice cleaner model is `models/voice-cleaner/std.rnnn`.

## Build, Test, and Development Commands

- `powershell -ExecutionPolicy Bypass -File .\src\init_python_env.ps1`: create and validate the local Python 3.12 `.venv`, then install `requirements.txt` and optional WhisperX dependencies.
- `.\.venv\Scripts\python.exe -m unittest discover -s src -p "test_*.py"`: run the full unit test suite.
- `powershell -ExecutionPolicy Bypass -File .\src\traducir_subs_mkv.ps1 -InputMkv ".\input\video.mkv"`: run the MKV subtitle translation workflow.
- `powershell -ExecutionPolicy Bypass -File .\src\transcribe_video_audio.ps1 -InputVideo ".\input\video.mkv"`: transcribe video audio and produce a subtitled MKV.
- `powershell -ExecutionPolicy Bypass -File .\src\clean_video_voice.ps1 -InputVideo ".\input\video.mkv"`: generate cleaned audio or a cleaned MKV.

External tools must be on `PATH`: `ffmpeg`, `ffprobe`, and `mkvmerge`.

## Coding Style & Naming Conventions

Use Python 3.12-compatible code, four-space indentation, and clear `snake_case` names for modules, functions, variables, and test methods. Keep PowerShell parameters descriptive and PascalCase, matching existing scripts such as `-InputMkv` and `-WorkspaceId`. Prefer `pathlib.Path` for filesystem logic. Route generated artifacts through the workspace folders above.

## Testing Guidelines

Tests use the standard library `unittest` framework and are named `src/test_*.py`. Add focused tests next to the module being changed, especially for path resolution, subtitle text conversion, language detection, normalization, and workspace layout. Use temporary directories for filesystem behavior; do not require real media files in unit tests.

## Commit & Pull Request Guidelines

Recent commits use short imperative summaries, for example `Update README and pending tasks` and `Document dynamic maps and transcription fallback`. Follow that style: one concise subject line describing the change. Pull requests should include purpose, affected workflow, test output, and relevant media/tool assumptions. Include sample output paths when subtitles, MKVs, or reports changed.

## Security & Configuration Tips

Do not commit local videos, generated MKVs, transcripts, or private translation maps unless intentionally curated. Keep `.venv/`, `input/`, `output/`, and `subtitle_work/` as local working areas. Verify language and subtitle track selection with `ffprobe` or `mkvmerge -J` before running destructive or long workflows.
