# Formats

## Outputs

The transcription flow writes:

- `output/<workspace-id>/<stem>.transcribed.srt`
- `output/<workspace-id>/<stem>.transcribed.ass`
- `output/<workspace-id>/<stem>.transcribed.mkv`
- `subtitle_work/<workspace-id>/transcription_report.json`

Raw backend files stay in:

- `subtitle_work/<workspace-id>/whisper/`

## SRT

SRT is the embedded subtitle track in the transcribed MKV. It is simple, TV-safe, and easy for the translation flow to extract. It should use at most two visible lines per cue. Long backend cues should be split into sequential cues rather than rendered as three or more lines at once.

## ASS

ASS is generated as a simple companion file for inspection and for ASS-oriented processing. It should not contain karaoke effects, drawings, or positioning commands. The default style uses side margins near 10% so rendered text occupies about 80% of the video width.

## MKV

The final output is always an MKV. It keeps original tracks when the source container can be remuxed without re-encoding and adds one default subtitle track:

- language: detected/requested language when known;
- title: `Transcripción <idioma>`;
- codec: SubRip/SRT.
