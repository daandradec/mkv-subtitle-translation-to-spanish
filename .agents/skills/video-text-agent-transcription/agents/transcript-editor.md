# Transcript Editor

Review transcript quality after backend output exists.

- Focus on cleanup that should become reproducible in `src/text_transcription_postprocess.py`.
- Remove noise, excessive filler, duplicate fragments, boilerplate, empty greetings, and sponsorship clutter.
- Preserve substantive content, domain terms, examples, decisions, methods, and explanations.
- Flag suspicious encoding artifacts such as replacement characters or question marks replacing accents.
