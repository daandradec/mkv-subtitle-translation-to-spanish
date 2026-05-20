# Subtitle Format Guidance

## ASS

Use ASS when styling, signs, positioning, or embedded fonts matter and the target player supports ASS well. Preserve timing and style metadata, but avoid exposing effect commands as text.

Risks:

- Complex karaoke may be stored as per-character events.
- Vector drawing events can look like text after naive parsing.
- Some TVs render ASS effects poorly or show command/path fragments.

## Plain ASS

Use plain ASS as a compatibility compromise when the source is ASS but complex effects must be simplified. Keep basic styles and positions only when safe. Replace karaoke/effect-heavy lyrics with full-line readable Spanish.

## SRT

Use SRT for TV-safe output when styling is less important than compatibility. It is usually safer for USB playback on TVs but loses signs, positioning, fonts, and advanced styling.

## Recommended Output Strategy

- Desktop/fidelity output: MKV with translated ASS or simplified ASS.
- TV-safe output: SRT or plain ASS with no karaoke effects, drawing commands, or per-character events.
- If the source subtitle has complex songs/signs, generate both when feasible.

## Unsafe Text Patterns

Treat these as non-translatable unless a parser reconstructs visible text confidently:

- ASS override tags like `{\pos(...)}`, `{\move(...)}`, `{\t(...)}`.
- Drawing mode tags like `\p1`, `\p2`, etc.
- Vector path data such as long sequences of `m`, `l`, `b`, and numbers.
- Per-letter karaoke events that only contain one or two characters.
