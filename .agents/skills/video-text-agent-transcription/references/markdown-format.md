# Markdown Format

The Markdown is designed for future RAG ingestion and human review. Canonical SRT, VTT, and TXT outputs use the same cleaned transcript text.

Required structure:

- YAML frontmatter with title, source video, backend, language, audio stream, and generation time.
- H1 with the video name.
- H2 sections using one time range per paragraph, derived from the clean transcript timing.
- Paragraphs that read naturally and preserve the spoken meaning.

Cleanup priorities:

- Remove nonverbal noise, empty greetings, repeated boilerplate, sponsorship clutter, and excessive fillers.
- Preserve concepts, procedures, examples, decisions, technical names, and domain terminology.
- Keep UTF-8 valid and repair obvious Spanish inverted question marks when transcription text contains `?Es`, `?Que`, or similar artifacts.
- Repair common mojibake sequences before writing Markdown and keep source-code cleanup rules ASCII-safe with Unicode escapes.
- If backend metadata says English but the text strongly matches Spanish markers, report the Markdown language as Spanish.
- Keep semantic corrections conservative. Prefer punctuation and obvious transcription fixes over deleting spoken content.
- Avoid aggressive summarization. This is a cleaned transcript, not a summary.

When `-Verbatim` is selected, skip semantic corrections, boilerplate/noise/filler removal, repeated-word removal, and duplicate-segment removal. Only repair encoding artifacts and normalize whitespace. Record `postprocess_mode: verbatim` in Markdown and the report.
