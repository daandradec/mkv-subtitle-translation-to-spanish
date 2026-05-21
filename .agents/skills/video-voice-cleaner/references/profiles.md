# Profiles

## conservative

Default. Uses moderate RNNoise, light FFT denoise, light non-local denoise, gentle gate, small voice EQ boosts, soft compression, and loudness normalization. Best when natural voice quality matters.

## balanced

Uses stronger denoise and presence boosts than `conservative`. Best when background noise clearly hurts intelligibility but the user still wants natural audio.

## asr

Uses the strongest denoise and compression in v1. Best when Whisper/WhisperX recognition is the priority. Warn the user that this profile has the highest risk of digital artifacts.

## Rule

Never add fixed timestamp ducking unless a future user explicitly requests a targeted repair for a known noise event. v1 must remain general-purpose.
