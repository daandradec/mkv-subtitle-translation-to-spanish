# Testing

Before finishing script changes, run:

```powershell
.\.venv\Scripts\python.exe -m py_compile .\src\text_transcription_workspace.py .\src\text_transcription_postprocess.py
.\.venv\Scripts\python.exe .\src\test_text_transcription.py
.\.venv\Scripts\python.exe -m unittest discover -s .\src -p "test_*.py"
```

Also parse the PowerShell script:

```powershell
$null = [System.Management.Automation.Language.Parser]::ParseFile(
  (Resolve-Path .\src\transcribe_video_text.ps1),
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
