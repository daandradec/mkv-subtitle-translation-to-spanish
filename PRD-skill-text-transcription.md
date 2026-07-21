# PRD: Skill `video-generate-whisper-transcription`

## Resumen

Crear una skill local independiente para transcribir videos a texto con WhisperX como backend preferido y OpenAI Whisper como fallback local. La skill procesa un archivo de video o todos los videos de una carpeta, publica sólo SRT/Markdown y conserva los demás formatos bajo debug para trazabilidad.

Este flujo no genera subtitulos incrustados, no remuxea el video y no traduce. Su objetivo es producir transcripciones textuales de alta calidad, velocidad y trazabilidad.

## Objetivos

- Procesar un video individual en `input/<video>` o una carpeta como `input/`.
- Usar WhisperX cuando este disponible; usar Whisper si WhisperX no esta disponible.
- Crear salidas deterministas por video en `output/<stem>/`, sin hash ni sufijo aleatorio.
- Mantener `json` y `tsv` como artefactos cercanos al backend cuando existan.
- Publicar únicamente `.srt` y `<videoname>.md` canónicos con transcripción limpia; conservar VTT/TXT limpios como auxiliares de debug.
- Aplicar limpieza general y especifica por idioma detectado cuando existan reglas disponibles.

## No Objetivos

- No crear MKV final ni incrustar subtitulos.
- No traducir entre idiomas.
- No depender de API keys ni servicios externos.
- No reemplazar `video-generate-new-subtitles-from-audio`; esta skill es solo textual.

## Flujo

1. Validar que existan `ffmpeg` y `ffprobe`.
2. Inicializar `.venv` con Python 3.12 usando `src/shared/powershell/init_python_env.ps1`.
3. Resolver entrada:
   - archivo: procesa ese video;
   - carpeta: procesa videos validos no recursivamente y por orden de nombre;
   - sin parametro: procesa solo si hay exactamente un video valido en `input/`.
4. Para cada video:
   - seleccionar audio por `-AudioStreamIndex`, default del contenedor o primera pista;
   - limpiar de forma segura y crear `output/<stem>/`;
   - extraer WAV mono 16 kHz a `output/<stem>/debug/video-generate-whisper-transcription/audio/`;
   - ejecutar WhisperX o Whisper con `--output_format all`;
   - conservar todos los formatos nativos en `output/<stem>/debug/video-generate-whisper-transcription/whisper/raw/`;
   - publicar el SRT limpio y generar VTT/TXT limpios en `whisper/postprocess/`;
   - leer los artefactos Whisper y generar `<videoname>.md`;
   - escribir `text_transcription_report.json` bajo `debug/video-generate-whisper-transcription/reports/`.
5. En batch, continuar con los demas videos si uno falla y reportar fallos al final.

## Interfaz

Skill:

```text
$video-generate-whisper-transcription "input/video.mp4"
$video-generate-whisper-transcription "input/"
```

Script:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\video-generate-whisper-transcription\transcribe_video_text.ps1 `
  -InputPath ".\input\video.mp4" `
  -Backend auto `
  -WhisperXModel large-v3 `
  -WhisperModel turbo `
  -Device cuda `
  -ComputeType float16 `
  -BatchSize 8
```

Parametros:

- `-InputPath`: archivo o carpeta. Si falta, usa autodeteccion estricta en `input/`.
- `-Backend`: `auto`, `whisperx` o `whisper`.
- `-Language`: opcional; si falta, WhisperX/Whisper autodetecta.
- `-AudioStreamIndex`: opcional; `-1` usa default o primera pista.
- `-DryRun`: muestra comandos sin transcribir.

## Markdown para RAG

El Markdown generado debe:

- incluir frontmatter con video fuente, backend, idioma, pista de audio y fecha;
- usar secciones con rangos de tiempo para trazabilidad;
- agrupar texto en parrafos legibles;
- eliminar ruido no verbal, boilerplate de subtitulos, saludos vacios, patrocinios repetitivos, relleno verbal excesivo y duplicados;
- conservar conceptos, metodologias, ejemplos, decisiones de diseno, mejores practicas y contenido tematico;
- escribirse en UTF-8 y evitar caracteres corruptos.

## Validacion

- `python -m py_compile` de los modulos nuevos.
- Parse del PowerShell principal.
- Tests unitarios para:
  - nombre de salida determinista y limpieza segura;
  - postproceso Markdown desde JSON;
  - limpieza de boilerplate, relleno y caracteres danados;
  - fallback de backend;
  - salida con nombres canonicos.
- Escenarios manuales:
  - un video individual;
  - carpeta con varios videos;
  - WhisperX ausente;
  - video sin audio;
  - batch con un video fallido y otros exitosos.

## Supuestos

- La transcripcion conserva el idioma original.
- La limpieza es local y reproducible.
- El usuario puede forzar idioma cuando la autodeteccion no sea suficiente.
- El postproceso puede corregir el idioma efectivo del Markdown y salidas textuales canonicas cuando la metadata del backend contradice el texto transcrito.
- Las correcciones semanticas deben ser conservadoras: mejorar puntuacion y errores obvios sin borrar contenido hablado.
- Los outputs generados permanecen ignorados por Git.
