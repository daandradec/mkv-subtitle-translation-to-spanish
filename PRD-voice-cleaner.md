# PRD: Video Voice Cleaner

## Resumen

Crear una skill local independiente `video-voice-cleaner` para sanitizar, normalizar y aclarar voces en videos con ruido de fondo antes de una posible transcripcion con Whisper o WhisperX. La skill produce un MKV nuevo con video copiado, audio limpio en FLAC como pista default y audio original conservado como alternativa.

La skill no se conecta automaticamente con `video-subtitle-agentic-transcription`. El usuario decide si primero limpia el video y luego usa el MKV resultante como entrada de transcripcion.

## Objetivos

- Mejorar inteligibilidad de voz sin provocar un sonido digital, metalico o robotico.
- Usar un flujo general, no hardcodeado a un minuto o ruido especifico.
- Mantener trazabilidad con reportes, diagnosticos y muestras opcionales.
- Conservar el audio original dentro del MKV final para comparar o recuperar referencia.
- Evitar dependencias globales distintas de FFmpeg, FFprobe y MKVToolNix.

## Flujo

1. Validar entrada de video con audio usando `ffprobe`.
2. Seleccionar pista de audio:
   - `-AudioStreamIndex` si el usuario lo pasa;
   - si no, audio default;
   - si no hay default, primer audio.
3. Limpiar de forma segura y crear `output/<stem>/`; guardar helpers en `output/<stem>/debug/video-voice-cleaner/`.
4. Validar modelo RNNoise versionado en `models/voice-cleaner/std.rnnn`.
5. Crear un FLAC premaster con filtros conservadores de voz:
   - `adeclip`;
   - `highpass` / `lowpass`;
   - `arnndn`;
   - `afftdn`;
   - `anlmdn`;
   - `agate`;
   - ecualizacion de voz;
   - de-esser;
   - compresion suave;
   - limitador.
6. Ejecutar loudness normalization en dos pasadas hacia `I=-16`, `LRA=9`, `TP=-2`.
7. Generar FLAC limpio final.
8. Remuxear MKV con:
   - pistas originales preservadas;
   - audios originales no-default;
   - audio limpio FLAC como default;
   - video sin recodificar cuando `mkvmerge` lo permita.
9. Escribir reporte `voice_cleaner_report.json`.
10. Opcionalmente generar muestras antes/despues.

## Perfiles

- `conservative`: default. Maxima naturalidad, reduccion de ruido moderada y bajo riesgo de artefactos.
- `balanced`: mas presencia e inteligibilidad, con riesgo moderado de colorear la voz.
- `asr`: prioriza claridad para ASR, con mayor reduccion de ruido y mayor riesgo de sonido artificial.

## Interfaz

```powershell
powershell -ExecutionPolicy Bypass -File .\src\video-voice-cleaner\clean_video_voice.ps1 `
  -InputVideo ".\input\video.mp4" `
  -Profile conservative `
  -AudioStreamIndex -1 `
  -OutputFormat mkv
```

Parametros:

- `-InputVideo`: ruta del video. Si falta, auto-detecta solo cuando hay exactamente un video con audio en `input/`.
- `-AudioStreamIndex`: opcional; `-1` usa default, luego primer audio.
- `-Profile`: `conservative`, `balanced`, `asr`; default `conservative`.
- `-OutputFormat`: `mkv` en v1.
- `-KeepTemp`: conserva premaster FLAC.
- `-GenerateSamples`: genera clips cortos antes/despues.
- `-DryRun`: muestra rutas, pista elegida y cadena de filtros sin procesar audio.

Entregables:

- `output/<stem>/<stem>.voice-cleaned.mkv`
- `output/<stem>/<stem>.voice-cleaned.flac`
- `output/<stem>/debug/video-voice-cleaner/reports/voice_cleaner_report.json`
- diagnosticos en `output/<stem>/debug/video-voice-cleaner/work/`
- muestras opcionales en `output/<stem>/debug/video-voice-cleaner/samples/`

## Skill

La skill `.agents/skills/video-voice-cleaner/` debe instruir al agente principal a coordinar:

- inspector de audio/contenedor;
- disenador de perfil de limpieza;
- ejecutor FFmpeg;
- revisor de calidad auditiva/ASR;
- validador tecnico de MKV/audio.

La skill debe recordar que el flujo es independiente: no invoca transcripcion automaticamente y no modifica `video-subtitle-agentic-transcription`.

## Validacion

- Parse PowerShell de `src/video-voice-cleaner/clean_video_voice.ps1`.
- `py_compile` de modulos Python.
- Unit tests para:
  - rutas de workspace;
  - perfiles y cadenas FFmpeg;
  - parse de JSON loudnorm;
  - ausencia de reglas hardcodeadas de tiempo;
  - modelo RNNoise versionado.
- Dry-run con un video real:
  - selecciona audio correcto;
  - muestra filtro;
  - no genera archivos de salida pesados.
- Escenario completo:
  - conserva video;
  - conserva audio original;
  - agrega FLAC limpio default;
  - genera reporte;
  - el MKV limpio puede usarse manualmente con `video-subtitle-agentic-transcription`.

## Supuestos

- El modelo `std.rnnn` del proyecto temporal se copia a `models/voice-cleaner/std.rnnn` y queda versionado.
- El proyecto temporal `voice_cleaner_recorder_video_flac_audio/` no se modifica ni se borra durante esta implementacion.
- El audio limpio se prioriza para naturalidad y ASR, no para masterizacion musical.
- v1 no intenta detectar automaticamente secciones puntuales de ruido extremo; evita reglas de tiempo hardcodeadas.
