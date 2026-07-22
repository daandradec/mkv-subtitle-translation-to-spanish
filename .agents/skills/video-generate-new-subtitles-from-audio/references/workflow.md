# Workflow

## 1. Prepare Input

- Use `inputs/` as the canonical folder.
- Process only one video per run.
- Accept any video file with audio that FFmpeg/Whisper can decode. Common examples include MKV, MP4, MOV, M4V, WebM, AVI, WMV, FLV, TS/M2TS, MPEG/MPG, 3GP/3G2, and OGV.
- Initialize `.venv/` with Python 3.12 using `scripts/manage_video_toolkit.ps1 setup-python-environment` on Windows or `scripts/manage_video_toolkit.sh setup-python-environment` on Ubuntu before running Python modules or transcription executables.
- Use `.venv/Scripts` first in PATH so `whisperx` and `whisper` come from the project environment.
- Use `outputs/<stem>/`, where `<stem>` is the exact input filename without extension.
- A fresh run safely clears that directory and writes helpers under `outputs/<stem>/debug/video-generate-new-subtitles-from-audio/`. Random/hash suffixes and custom workspace ids are not supported.

## 2. Inspect Audio

- Use `ffprobe` to inspect audio streams.
- Select requested audio index when the optional `-AudioStreamIndex` parameter is provided.
- Otherwise select default audio, then first audio.
- If multiple audio streams are marked default, use the first one in container order and warn that `-AudioStreamIndex` can override the choice.
- If `-Language` is not provided, derive the backend language from the selected audio stream metadata and pass it explicitly to WhisperX/Whisper.
- Stop if no audio streams exist.

## 3. Extract Audio

- Extract WAV mono 16 kHz with FFmpeg.
- Keep audio in `outputs/<stem>/debug/video-generate-new-subtitles-from-audio/audio/`.

## 4. Transcribe

- Prefer WhisperX installed in `.venv/`.
- Fallback to `openai-whisper` installed in `.venv/` if WhisperX is missing.
- Preserve original spoken language.
- Do not use translation mode.
- Keep raw outputs in `outputs/<stem>/debug/video-generate-new-subtitles-from-audio/whisper/`.

## 5. Postprocess

- Clean SRT cues and reject empty transcription.
- Limit visible subtitles to two lines per cue.
- Split long cues into sequential cues inside the same original time range instead of stacking three or more lines.
- Prefer WhisperX word timestamps for split cue start/end times; if unavailable, distribute timing proportionally inside the original cue.
- Keep ASS companion subtitles constrained to about 80% of video width by using 10% side margins.
- Keep the clean SRT under `outputs/<stem>/debug/video-generate-new-subtitles-from-audio/postprocess/`; it is an internal remux input.
- Do not generate or publish ASS during postprocessing.
- Write `transcription_report.json`.

## 6. Remux

- Output must always be an MKV.
- Detect the source container with `ffprobe`.
- For native Matroska/WebM, use `mkvmerge` directly.
- For MP4/MOV and every other non-Matroska source, map the source and transcription SRT into the final MKV in one FFmpeg invocation. A shared mux operation applies the same automatically calculated timestamp shift to video, audio, and subtitles when edit lists or negative preroll exist.
- Never remux a non-Matroska source into a source-only intermediate and then add the SRT in a separate command. Separate commands can normalize timestamps differently and create a constant subtitle offset.
- Do not fix edit-list offsets with a hardcoded subtitle delay or `-ss 0`. Stream-copy trimming at zero can discard video until the next keyframe.
- Preserve original tracks when the source container allows copy remuxing.
- Embed the transcribed SRT as default with title `Transcripción <idioma>`.
- Validate that all embedded cue timestamps differ from their source SRT timestamps by one uniform mux shift (maximum spread 5 ms), and record the strategy and shift in `outputs/<stem>/debug/video-generate-new-subtitles-from-audio/reports/remux_validation.json`.
- By default, publish only `<stem>.transcribed.mkv` in `outputs/<stem>/`; a fresh run removes obsolete same-stem sidecars before processing.
- With `--export-ass-file-subtitles`, extract the normalized embedded subtitle track from the completed MKV, convert it to ASS, validate its cue count and timestamps against the embedded packets, and publish it in `outputs/<stem>/sidecars/`.

## 7. Handoff

- The generated MKV can be passed to `video-generate-traslated-subtitles-from-existing-subtitles`.
- If detected language is unsupported by translation, report that transcription succeeded but translation may stop.
