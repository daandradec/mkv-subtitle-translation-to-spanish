# Formats

## Outputs

The transcription flow writes:

- `outputs/<stem>/<stem>.transcribed.mkv`
- optional `outputs/<stem>/sidecars/<stem>.transcribed.ass` with `--export-ass-file-subtitles`
- internal `outputs/<stem>/debug/video-generate-new-subtitles-from-audio/postprocess/<stem>.transcribed.srt`
- `outputs/<stem>/debug/video-generate-new-subtitles-from-audio/reports/transcription_report.json`
- `outputs/<stem>/debug/video-generate-new-subtitles-from-audio/reports/remux_validation.json`

Raw backend files stay in:

- `outputs/<stem>/debug/video-generate-new-subtitles-from-audio/whisper/`

## SRT

SRT is the internal source for the embedded subtitle track in the transcribed MKV. It is simple, TV-safe, and easy for the translation flow to extract. It should use at most two visible lines per cue. Long backend cues should be split into sequential cues rather than rendered as three or more lines at once. It must not be published beside the MKV because its pre-remux timeline can differ from the normalized Matroska timeline.

## ASS

ASS is optional. When `--export-ass-file-subtitles` is requested, it is generated only from a temporary extraction of the already normalized embedded MKV track and stored in the `sidecars/` subdirectory. It must not contain karaoke effects, drawings, or positioning commands. The default style uses side margins near 10% so rendered text occupies about 80% of the video width.

## MKV

The final output is always an MKV. It keeps original tracks when the source container can be remuxed without re-encoding and adds one default subtitle track:

- language: detected/requested language when known;
- title: `Transcripción <idioma>`;
- codec: SubRip/SRT.

For non-Matroska inputs, media and SRT must enter the final FFmpeg remux together. Containers with edit lists may expose lossless preroll in the MKV, but the shared mux timeline keeps the transcription synchronized without a fixed delay. Removing preroll that ends between video keyframes would require video re-encoding and is outside this lossless workflow.

The default output directory contains no same-stem SRT/ASS sidecars, preventing players from overriding the synchronized embedded track with an unsafe `[Local]` subtitle.
