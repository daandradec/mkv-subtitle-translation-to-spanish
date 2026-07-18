# PRD: Skill `video-text-agent-transcription`

## Resumen

Crear una skill local independiente para transcribir videos a texto con WhisperX como backend preferido y OpenAI Whisper como fallback local. La skill procesa un archivo de video o todos los videos de una carpeta, conserva JSON/TSV cercanos al backend y genera SRT/VTT/TXT/Markdown limpios por video para uso futuro como base de conocimiento o RAG.

Este flujo no genera subtitulos incrustados, no remuxea el video y no traduce. Su objetivo es producir transcripciones textuales de alta calidad, velocidad y trazabilidad.

## Objetivos

- Procesar un video individual en `input/<video>` o una carpeta como `input/`.
- Usar WhisperX cuando este disponible; usar Whisper si WhisperX no esta disponible.
- Crear salidas por video en `output/<prefijo-24>-<codigo-6>/`.
- Mantener `json` y `tsv` como artefactos cercanos al backend cuando existan.
- Generar `.srt`, `.vtt`, `.txt` y `<videoname>.md` canonicos con transcripcion limpia, manteniendo tiempos en subtitulos y Markdown estructurado por rangos de tiempo.
- Aplicar limpieza general y especifica por idioma detectado cuando existan reglas disponibles.

## No Objetivos

- No crear MKV final ni incrustar subtitulos.
- No traducir entre idiomas.
- No depender de API keys ni servicios externos.
- No reemplazar `video-subtitle-agentic-transcription`; esta skill es solo textual.

## Flujo

1. Validar que existan `ffmpeg` y `ffprobe`.
2. Inicializar `.venv` con Python 3.12 usando `src/init_python_env.ps1`.
3. Resolver entrada:
   - archivo: procesa ese video;
   - carpeta: procesa videos validos no recursivamente y por orden de nombre;
   - sin parametro: procesa solo si hay exactamente un video valido en `input/`.
4. Para cada video:
   - seleccionar audio por `-AudioStreamIndex`, default del contenedor o primera pista;
   - crear workspace unico con formato `24 + "-" + 6`;
   - extraer WAV mono 16 kHz a `subtitle_work/<workspace-id>/text-transcription/`;
   - ejecutar WhisperX o Whisper con `--output_format all`;
   - normalizar nombres de archivos nativos a `<videoname>.*`;
   - reescribir `.srt`, `.vtt` y `.txt` canonicos con texto postprocesado;
   - leer JSON/SRT/VTT/TXT y generar `<videoname>.md`;
   - escribir `text_transcription_report.json`.
5. En batch, continuar con los demas videos si uno falla y reportar fallos al final.

## Interfaz

Skill:

```text
$video-text-agent-transcription "input/video.mp4"
$video-text-agent-transcription "input/"
```

Script:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\transcribe_video_text.ps1 `
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
- `-WorkspaceId`: opcional y solo para un video.
- `-Force`: permite reutilizar un `WorkspaceId` existente.
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
  - workspace unico;
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
