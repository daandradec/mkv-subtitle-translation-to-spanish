# Testing

Before finishing script changes, run:

```powershell
$env:PYTHONPATH = ".\src\shared\python;.\src\video-generate-whisper-transcription\python"
.\.venv\Scripts\python.exe -m unittest discover -s .\src\video-generate-whisper-transcription\tests -p "test_*.py"
powershell -ExecutionPolicy Bypass -File .\src\shared\powershell\run_tests.ps1
```

Also parse the PowerShell script:

```powershell
$null = [System.Management.Automation.Language.Parser]::ParseFile(
  (Resolve-Path .\src\video-generate-whisper-transcription\transcribe_video_text.ps1),
  [ref]$null,
  [ref]$null
)
```

Manual scenarios:

- Single video file.
- Folder input with multiple videos.
- Video without audio.
- WhisperX unavailable with Whisper fallback.
- Batch where one video fails and another succeeds.
