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

SRT is the embedded subtitle track in the transcribed MKV. It is simple, TV-safe, and easy for the translation flow to extract.

## ASS

ASS is generated as a simple companion file for inspection and for ASS-oriented processing. It should not contain karaoke effects, drawings, or positioning commands.

## MKV

The MKV keeps original tracks and adds one default subtitle track:

- language: detected/requested language when known;
- title: `Transcripción <idioma>`;
- codec: SubRip/SRT.
