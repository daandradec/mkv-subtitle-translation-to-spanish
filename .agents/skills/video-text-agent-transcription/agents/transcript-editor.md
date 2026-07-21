# Transcript Editor

Review transcript quality after backend output exists.

- Focus on cleanup that should become reproducible in `src/video-text-agent-transcription/python/video_text_agent_transcription/postprocess.py`.
- Remove noise, excessive filler, duplicate fragments, boilerplate, empty greetings, and sponsorship clutter.
- Preserve substantive content, domain terms, examples, decisions, methods, and explanations.
- Flag suspicious encoding artifacts such as replacement characters or question marks replacing accents.
