# MKV Subtitle Translation to Spanish

Workflow reproducible para extraer una pista de subtitulos textual desde un MKV, traducirla al espanol LatAm y crear una copia del MKV con dos pistas espanolas embebidas: `Español LatAm` en ASS y `Español LatAm TV-safe` en SRT para reproductores o televisores que renderizan mal ASS complejo.

El repositorio contiene los scripts y mapas de traduccion. Los videos, subtitulos extraidos y archivos de trabajo pesados quedan ignorados por Git.

## Requisitos

- Windows PowerShell.
- Python 3.12 instalado y disponible con `py -3.12` o en PATH.
- FFmpeg disponible en PATH:
  - `ffmpeg`
  - `ffprobe`
- MKVToolNix disponible en PATH:
  - `mkvmerge`
- Dependencias Python instaladas automaticamente en `.venv/`:
  - `whisperx` recomendado para mejores timestamps;
  - `whisper` de `openai-whisper` como fallback local.

Instalacion sugerida con Chocolatey:

```powershell
choco install python312 ffmpeg mkvtoolnix -y
```

Verifica:

```powershell
py -3.12 --version
ffmpeg -version
ffprobe -version
mkvmerge --version
```

## Entorno Python Local

El proyecto no usa el Python global para ejecutar los flujos. Antes de traducir o transcribir, los scripts inicializan y activan automaticamente un entorno virtual local en `.venv/` con Python 3.12.

Ese entorno instala las dependencias requeridas declaradas en `requirements.txt` y luego intenta instalar WhisperX desde `requirements-whisperx.txt` como backend preferido. Esto evita el problema de Python 3.14, porque WhisperX en PyPI requiere Python `>=3.10,<3.14`. Si WhisperX falla por alguna dependencia, el flujo puede continuar con `openai-whisper` desde el mismo `.venv/`.

Tambien puedes inicializarlo manualmente:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\init_python_env.ps1
```

Durante cada flujo, los scripts agregan `.venv\Scripts` al inicio del PATH y usan `.venv\Scripts\python.exe`. Por eso `whisperx` y `whisper` deben resolverse desde el entorno local, no desde instalaciones globales.

Si `mkvmerge` existe pero PowerShell no lo detecta, cierra y vuelve a abrir la terminal. En instalaciones manuales de MKVToolNix, agrega esta carpeta al PATH si aplica:

```powershell
C:\Program Files\MKVToolNix
```

## Archivos Principales

- `src\traducir_subs_mkv.ps1`: orquesta todo el flujo.
- `src\ass_apply_translations.py`: aplica las traducciones sobre el ASS sin cambiar tiempos.
- `src\ass_to_tv_safe_srt.py`: crea un SRT limpio sin tags ASS, dibujos vectoriales ni efectos karaoke.
- `src\normalize_spanish_subtitles.py`: normaliza el texto visible del ASS y regenera el SRT TV-safe desde el ASS normalizado.
- `src\subtitle_text_to_ass.py`: convierte subtitulos extraidos `.srt`, `.vtt` o `.webvtt` a un ASS simple para que puedan entrar a etapas que esperan ASS.
- `src\subtitle_language.py` y `src\languages\`: validan que la pista fuente este en la lista de idiomas soportados.
- `src\subtitle_workspace.py`: crea carpetas dedicadas por ejecucion para `subtitle_work/`, `translations/` y `output/`.
- `src\translation_maps.py`: resuelve mapas JSON por workspace e idioma fuente.
- `src\normalize_translation_maps.py`: sanea mapas JSON antes de aplicarlos y detiene el flujo si quedan signos `?` sospechosos por texto corrupto.
- `src\translation_terms.py`: aplica glosarios locales para normalizar nombres propios y terminos recurrentes.
- `src\transcribe_video_audio.ps1`: transcribe audio de un video sin subtitulos y genera un MKV con subtitulos transcritos.
- `src\transcription_backend.py`, `src\transcription_workspace.py`, `src\transcription_postprocess.py`: soporte para backend WhisperX/Whisper, workspaces y postproceso de transcripcion.
- `src\clean_video_voice.ps1` y `src\voice_cleaner.py`: limpian, aclaran y normalizan voces en un video antes de una posible transcripcion.
- `src\init_python_env.ps1`: crea y valida `.venv` con Python 3.12 e instala dependencias desde `requirements.txt`.
- `requirements.txt`: dependencias Python requeridas del proyecto.
- `requirements-whisperx.txt`: dependencia preferida de WhisperX para mejores timestamps.
- `src\test_*.py`: pruebas unitarias.
- `translations\`: mapas de traduccion locales. Esta carpeta esta ignorada por Git y no se sube al repositorio. Todos los idiomas, incluido ingles, usan `translations\<workspace-id>\<idioma>\`.
- `.gitignore`: excluye videos, subtitulos extraidos, caches y temporales.

El video fuente y el MKV final no se versionan. Por defecto, coloca entradas en `input/` y revisa resultados en `output/`.

Validaciones de entrada:

- Si `input/` no contiene ningun MKV y no indicas `-InputMkv`, el flujo se detiene. Un archivo de video `.mkv` con subtitulos incrustados es obligatorio para ejecutar la traduccion.
- Si `input/` contiene varios MKV, el flujo no elige automaticamente. Debes indicar exactamente un archivo con `-InputMkv`.
- Si el MKV seleccionado no tiene subtitulos incrustados, el flujo se detiene y avisa que no se encontraron subtitulos en el archivo original para traducir a espanol.
- `input/` es la carpeta canonica. Si escribes `inputs\archivo.mkv`, corrige a `input\archivo.mkv` cuando ese archivo exista.

Si un video no tiene subtitulos incorporados, usa primero la skill `video-subtitle-agentic-transcription` para crear subtitulos desde el audio. El MKV transcrito puede usarse despues como entrada de `mkv-subtitle-agentic-translation` cuando el idioma resultante sea soportado.

Cada ejecucion crea workspaces dedicados para no mezclar artefactos de distintos videos:

```text
subtitle_work\<prefijo-24>-<codigo-6>\
translations\<prefijo-24>-<codigo-6>\
output\<prefijo-24>-<codigo-6>\
```

El prefijo se arma con palabras completas del nombre del MKV, hasta 24 caracteres, y el mismo identificador se usa en `subtitle_work`, `translations` y `output`.

## Flujo Opcional De Limpieza De Voz

Usa este flujo cuando el audio de un video tenga ruido de fondo, voces poco claras o loudness irregular. Es independiente: no transcribe, no traduce y no llama automaticamente a otras skills. El resultado es un MKV nuevo que puedes usar despues con `video-subtitle-agentic-transcription` si quieres.

Para grabaciones con ruido ambiental fuerte, primero conviene hacer una limpieza manual ligera en una herramienta especializada como Audacity, ElevenLabs o Adobe, evitando procesamientos agresivos que vuelvan la voz metalica o artificial. Despues usa `video-voice-cleaner` como una segunda pasada reproducible para normalizar loudness, aclarar la voz y preparar mejor el audio para Whisper/WhisperX.

```powershell
powershell -ExecutionPolicy Bypass -File .\src\clean_video_voice.ps1 `
  -InputVideo ".\input\video.mp4" `
  -Profile conservative `
  -AudioStreamIndex -1 `
  -OutputFormat mkv
```

Tambien puedes pasar una carpeta para limpiar todos los videos validos de forma no recursiva:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\clean_video_voice.ps1 `
  -InputVideo ".\input" `
  -Profile conservative
```

En modo carpeta, cada video recibe su propio `output\<workspace-id>\` y `subtitle_work\<workspace-id>\`. Si un archivo falla, el flujo continua con los demas y reporta el resumen al final. Si no pasas `-InputVideo`, el script conserva autodeteccion estricta y solo procesa cuando `input/` tiene exactamente un video valido.

Perfiles:

- `conservative`: default; prioriza voz natural y bajo riesgo de artefactos.
- `balanced`: mas limpieza e inteligibilidad.
- `asr`: prioriza claridad para Whisper/WhisperX, con mayor riesgo de sonido artificial.

El script:

1. Selecciona el audio default o el indicado con `-AudioStreamIndex`.
2. Valida el modelo RNNoise versionado en `models\voice-cleaner\std.rnnn`.
3. Aplica limpieza moderada de ruido, ecualizacion de voz, de-esser, compresion suave, limitador y loudness normalization en dos pasadas.
4. Genera:

```text
output\<workspace-id>\<stem>.voice-cleaned.mkv
output\<workspace-id>\<stem>.voice-cleaned.flac
subtitle_work\<workspace-id>\voice_cleaner_report.json
subtitle_work\<workspace-id>\voice-cleaner\
```

El MKV limpio conserva las pistas originales, desactiva el default en audios originales y agrega `Voz limpia FLAC` como pista de audio default. Para revisar sin procesar, usa `-DryRun`; para clips antes/despues, usa `-GenerateSamples`.

Invocacion desde Codex:

```text
[$video-voice-cleaner](C:\Development\Proyectos\Video\.agents\skills\video-voice-cleaner\SKILL.md) "input\video.mp4"
```

## Flujo Principal con PowerShell

Coloca el MKV fuente en `input/`:

```text
input\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].mkv
```

Luego ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\traducir_subs_mkv.ps1 `
  -InputMkv ".\input\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].mkv" `
  -EmbeddedSubtitleFormat both
```

El script hace lo siguiente:

1. Inicializa y activa `.venv` con Python 3.12.
2. Valida el MKV de entrada. Si indicas `-SourceSubtitleStreamIndex`, usa esa pista exacta; si no, usa la pista de subtitulos default cuando sea textual y soportada; si no hay default usable, selecciona la mejor pista textual soportada.
3. Crea un workspace dedicado en `subtitle_work\<workspace-id>\`, `translations\<workspace-id>\` y `output\<workspace-id>\`.
4. Extrae la pista de subtitulos seleccionada a `subtitle_work\<workspace-id>\*.source.ass`.
5. Resuelve mapas de traduccion desde `translations\<workspace-id>\<idioma>\` si no pasas `-TranslationJson`.
6. Sanea esos mapas en `subtitle_work\<workspace-id>\sanitized_translation_maps\` antes de aplicarlos y escribe `translation_map_quality_report.json`.
7. Genera `output\<workspace-id>\*.spa.ass`.
8. Genera `output\<workspace-id>\*.spa.srt` cuando pasas `-TvSafeSrt`.
9. Normaliza el espanol visible del ASS, corrige texto corrupto, limpia duplicados/puentes y regenera el SRT TV-safe desde ese ASS normalizado.
10. Crea un MKV nuevo con `mkvmerge`, sin recodificar video/audio. Usa `-EmbeddedSubtitleFormat both` para incrustar ASS y SRT, `srt` para solo TV-safe, o `ass` para solo ASS estilizado.
11. Conserva las pistas originales pero desactiva el default en todos los subtitulos originales. La pista `Español LatAm TV-safe` queda como `spa` y `default`; `Español LatAm` ASS queda incrustada como alternativa no-default.

Salida por defecto:

```text
output\<workspace-id>\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.mkv
output\<workspace-id>\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.ass
output\<workspace-id>\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.srt
```

Este flujo actual esta preparado para el caso ya trabajado y tambien puede seleccionar automaticamente una pista textual soportada cuando no se pasa indice. Para otros idiomas, mapas nuevos o subtitulos SRT/VTT incrustados, usa primero la inspeccion con agentes o los scripts auxiliares descritos abajo.
Si la pista fuente embebida es SRT/SubRip, VTT/WebVTT, `mov_text` o texto simple, el script la extrae y la convierte a ASS simple antes de aplicar traducciones.

## Flujo de Transcripcion

Usa este flujo cuando un video no tenga subtitulos incorporados y necesites crearlos desde el audio. La entrada puede ser cualquier archivo de video con audio que FFmpeg/Whisper pueda decodificar, por ejemplo MKV, MP4, MOV, M4V, WebM, AVI, WMV, FLV, TS/M2TS, MPEG/MPG, 3GP/3G2 u OGV. La salida final siempre sera MKV.

```powershell
powershell -ExecutionPolicy Bypass -File .\src\transcribe_video_audio.ps1 `
  -InputVideo ".\input\video.mp4" `
  -Backend auto `
  -WhisperXModel large-v3 `
  -WhisperModel turbo `
  -Device cuda `
  -ComputeType float16 `
  -BatchSize 8 `
  -MaxSubtitleLines 2 `
  -MaxSubtitleLineChars 52
```

El script:

1. Inicializa y activa `.venv` con Python 3.12.
2. Selecciona el audio default o el indicado opcionalmente con `-AudioStreamIndex`; si no pasas `-Language`, deriva el idioma desde la metadata de esa pista seleccionada.
3. Extrae audio WAV mono 16 kHz en `subtitle_work\<workspace-id>\`.
4. Usa WhisperX desde `.venv`; si no esta disponible, usa `openai-whisper` desde `.venv` como fallback.
5. Transcribe en el idioma original, sin traducir.
6. Postprocesa los subtitulos para mejorar legibilidad: maximo 2 lineas por cue, lineas de hasta 52 caracteres por defecto y ASS con margenes laterales de 10% para ocupar aproximadamente el 80% del ancho del video.
7. Genera:

```text
output\<workspace-id>\<stem>.transcribed.srt
output\<workspace-id>\<stem>.transcribed.ass
output\<workspace-id>\<stem>.transcribed.mkv
subtitle_work\<workspace-id>\transcription_report.json
```

El MKV transcrito incluye una pista SRT default con titulo `Transcripción <idioma>`. Si `mkvmerge` no puede leer el contenedor fuente directamente, el script crea primero un MKV intermedio en `subtitle_work\<workspace-id>\` con `ffmpeg -map 0 -c copy`. Si el idioma detectado no esta soportado por la skill de traduccion, el flujo avisa que la transcripcion es valida pero la traduccion posterior puede detenerse.
Cuando el idioma si esta soportado, `mkv-subtitle-agentic-translation` puede usar esa pista SRT transcrita como fuente y convertirla automaticamente a ASS para su pipeline interno.

## Flujo De Transcripcion A Texto

Usa `video-text-agent-transcription` cuando necesitas una transcripcion textual limpia para lectura, analisis o una futura base de conocimiento/RAG. Este flujo no crea MKV, no incrusta subtitulos y no traduce; solo genera los archivos nativos de WhisperX/Whisper y un Markdown optimizado.

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

Para priorizar la precision de WhisperX sobre la velocidad y conservar literalmente sus palabras en las salidas textuales:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\transcribe_video_text.ps1 `
  -InputPath ".\input\Auditoria 13 Mayo.mp4" `
  -Language es `
  -WhisperXQuality maximum `
  -WhisperXInitialPrompt "Clase virtual en espanol colombiano sobre auditoria, gestion organizacional y sistemas de gestion." `
  -WhisperXHotwords "DOFA, PESTEL, Classroom, auditoria, actividad economica, organizacion, partes interesadas, riesgos, oportunidades" `
  -Verbatim
```

El perfil `maximum` usa `beam_size=10`, `patience=2.0`, temperatura cero y conserva los valores convencionales de penalizacion y VAD. `-WhisperXBeamSize` y `-WhisperXPatience` permiten sobrescribir el perfil para pruebas A/B. `-Verbatim` solo normaliza codificacion y espacios: no elimina muletillas, repeticiones, ruido ni aplica correcciones semanticas.

Tambien puedes procesar todos los videos validos de `input/`:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\transcribe_video_text.ps1 -InputPath ".\input"
```

El script inicializa `.venv`, selecciona la pista de audio default o la indicada con `-AudioStreamIndex`, extrae WAV mono 16 kHz, ejecuta WhisperX o Whisper fallback y genera una carpeta unica por video:

```text
output\<workspace-id>\<stem>.json
output\<workspace-id>\<stem>.srt
output\<workspace-id>\<stem>.vtt
output\<workspace-id>\<stem>.txt
output\<workspace-id>\<stem>.tsv
output\<workspace-id>\<stem>.md
output\<workspace-id>\text_transcription_report.json
```

El postproceso reescribe las salidas textuales canonicas (`.srt`, `.vtt`, `.txt` y `.md`) con texto limpio, o literal cuando se usa `-Verbatim`. Conserva el JSON y TSV como artefactos cercanos al backend. El Markdown usa un heading temporal por parrafo, calculado desde los mismos segmentos del SRT, para que cada bloque de conocimiento tenga trazabilidad precisa al video. En modo limpio elimina ruido no verbal, relleno verbal excesivo, boilerplate de subtitulos, repeticiones, caracteres danados y aplica algunas correcciones semanticas conservadoras. Si WhisperX/Whisper reporta un idioma improbable frente al texto transcrito, el postproceso puede corregir el idioma efectivo para el Markdown, SRT/VTT/TXT y el reporte; si necesitas control total, fuerza el idioma con `-Language`. El reporte incluye el perfil, parametros, comando y versiones del backend para reproducir comparaciones.

Invocacion desde Codex:

```text
[$video-text-agent-transcription](C:\Development\Proyectos\Video\.agents\skills\video-text-agent-transcription\SKILL.md) "input\video.mp4"
[$video-text-agent-transcription](C:\Development\Proyectos\Video\.agents\skills\video-text-agent-transcription\SKILL.md) "input"
```

La skill local vive en:

```text
.agents\skills\video-subtitle-agentic-transcription\SKILL.md
```

Invocacion desde Codex:

```text
[$video-subtitle-agentic-transcription](C:\Development\Proyectos\Video\.agents\skills\video-subtitle-agentic-transcription\SKILL.md) "input\video.mp4"
```

## Idiomas Fuente Soportados

El flujo solo permite traducir hacia espanol desde estos idiomas fuente:

1. Ingles
2. Chino mandarin
3. Hindi
4. Portugues
5. Frances
6. Ruso
7. Aleman
8. Japones
9. Chino Wu (Shanghaines)
10. Coreano
11. Italiano

Si la metadata de la pista de subtitulos indica otro idioma, `src\traducir_subs_mkv.ps1` detiene la ejecucion y muestra la lista disponible. Para cualquier idioma soportado, incluido ingles, la ruta recomendada es usar la skill con subagentes para generar o validar mapas JSON locales en `translations\<workspace-id>\<idioma>\`. Si no pasas `-TranslationJson`, el script resuelve automaticamente esos mapas desde el workspace.

## Mapas de Traduccion

El flujo actual usa un esquema unico para todos los idiomas:

```text
translations\<workspace-id>\<idioma>\translations_all.json
translations\<workspace-id>\<idioma>\translations_chunk_01.json
translations\<workspace-id>\<idioma>\translations_dialogue_part1.json
```

El idioma es el codigo detectado por el pipeline, por ejemplo:

```text
translations\Love-Live-Nijigasaki-77826F\en\
translations\NIPPON-SANGOKU-2E6FBC\ja\
```

Reglas importantes:

- Ingles ya no usa mapas sueltos en la raiz de `translations/` como comportamiento principal.
- Si hay un `translations_all.json`, el script lo prefiere sobre mapas parciales.
- Si no existe `translations_all.json`, el script usa los archivos `translations_*.json` dentro de la carpeta del idioma.
- Los mapas antiguos de ingles pueden reutilizarse, pero deben copiarse o migrarse a `translations\<workspace-id>\en\`.
- Si no existen mapas para el workspace e idioma detectado, el script crea la carpeta esperada y se detiene para que el flujo agéntico genere los JSON antes de reintentar.
- Antes de aplicar cualquier mapa, `src\normalize_translation_maps.py` crea copias saneadas en `subtitle_work\<workspace-id>\sanitized_translation_maps\`.
- El saneamiento corrige patrones comunes de texto corrupto como `?Es`, `a?n`, `est?`, `Ry?mon`, tildes perdidas y algunos errores recurrentes de acentuacion.
- Si quedan signos `?` sospechosos despues del saneamiento, el flujo se detiene antes de generar el MKV para evitar subtitulos defectuosos.

## Uso con Otros Nombres

Puedes pasar rutas personalizadas:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\traducir_subs_mkv.ps1 `
  -InputMkv ".\entrada.mkv" `
  -WorkspaceId "entrada-demo-A1B2C3" `
  -EnglishAss ".\subtitle_work\entrada-demo-A1B2C3\entrada.source.ass" `
  -SpanishAss ".\output\entrada-demo-A1B2C3\entrada.spa.ass" `
  -TvSafeSrt ".\output\entrada-demo-A1B2C3\entrada.spa.srt" `
  -EmbeddedSubtitleFormat both `
  -OutputMkv ".\output\entrada-demo-A1B2C3\entrada.spa.mkv"
```

Si usas otro MKV, puedes dejar que el script seleccione automaticamente la mejor pista textual soportada, o revisar primero el indice de la pista de subtitulos con:

```powershell
ffprobe -hide_banner -i ".\entrada.mkv"
```

La seleccion automatica usa primero la pista de subtitulos `default` cuando sea textual y tenga idioma soportado. Si no existe una default usable, evita pistas `Forced` cuando hay pistas completas, evita CC/SDH salvo que se indique, prefiere mayor cobertura de eventos/duracion y considera la metadata del audio. Si quieres forzar otra pista, pasa `-SourceSubtitleStreamIndex`; normalmente el script resuelve el track ID de mkvmerge automaticamente, pero puedes pasar `-SourceMkvTrackId` si necesitas corregirlo manualmente:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\traducir_subs_mkv.ps1 `
  -InputMkv ".\input\entrada.mkv" `
  -SourceSubtitleStreamIndex 4 `
  -SourceMkvTrackId 4
```

## Flujo por Scripts Python

Los scripts tambien pueden usarse por piezas cuando estas preparando o depurando una pista de subtitulos.

Inicializa el entorno local antes de invocar modulos Python directamente:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\init_python_env.ps1
```

### 1. Extraer Subtitulos

Inspecciona el contenedor:

```powershell
ffprobe -hide_banner -i ".\input\entrada.mkv"
.\.venv\Scripts\python.exe .\src\subtitle_language.py --input-mkv ".\input\entrada.mkv" --list-candidates
.\.venv\Scripts\python.exe .\src\subtitle_workspace.py --input-mkv ".\input\entrada.mkv" --workspace-id "entrada-demo-A1B2C3"
```

Extrae una pista ASS:

```powershell
$streamIndex = 5
ffmpeg -y -i ".\input\entrada.mkv" -map "0:$streamIndex" -c:s copy ".\subtitle_work\entrada-demo-A1B2C3\entrada.source.ass"
```

Extrae una pista SRT o VTT si el contenedor la trae como texto:

```powershell
$streamIndex = 5
ffmpeg -y -i ".\input\entrada.mkv" -map "0:$streamIndex" -c:s copy ".\subtitle_work\entrada-demo-A1B2C3\entrada.source.srt"
```

El indice real puede variar; usa el resultado de `ffprobe`.

### 2. Convertir SRT/VTT a ASS

Cuando la pista fuente extraida sea `.srt`, `.vtt` o `.webvtt`, conviertela a ASS simple:

```powershell
.\.venv\Scripts\python.exe .\src\subtitle_text_to_ass.py `
  --input ".\subtitle_work\entrada-demo-A1B2C3\entrada.source.srt" `
  --output ".\subtitle_work\entrada-demo-A1B2C3\entrada.source.ass"
```

Para VTT:

```powershell
.\.venv\Scripts\python.exe .\src\subtitle_text_to_ass.py `
  --input ".\subtitle_work\entrada-demo-A1B2C3\entrada.source.vtt" `
  --output ".\subtitle_work\entrada-demo-A1B2C3\entrada.source.ass" `
  --format vtt
```

Este modulo preserva tiempos, limpia marcas comunes de SRT/VTT y genera eventos `Dialogue:` con estilo `Default`. Su objetivo es que una pista de texto no-ASS pueda ser tratada por etapas posteriores como si ya fuera ASS. No hace traduccion por si mismo.

### 3. Aplicar Mapas de Traduccion

Cuando uses scripts por piezas, sanea primero los mapas de traduccion:

```powershell
.\.venv\Scripts\python.exe .\src\normalize_translation_maps.py `
  --translations .\translations\entrada-demo-A1B2C3\ja\translations_all.json `
  --output-dir ".\subtitle_work\entrada-demo-A1B2C3\sanitized_translation_maps" `
  --report ".\subtitle_work\entrada-demo-A1B2C3\translation_map_quality_report.json"
```

Luego aplica los mapas saneados:

```powershell
.\.venv\Scripts\python.exe .\src\ass_apply_translations.py `
  --input-ass ".\subtitle_work\entrada-demo-A1B2C3\entrada.source.ass" `
  --output-ass ".\output\entrada-demo-A1B2C3\entrada.spa.ass" `
  --translations .\subtitle_work\entrada-demo-A1B2C3\sanitized_translation_maps\translations_all.json `
  --term-map .\translations\entrada-demo-A1B2C3\ja\term_map.json `
  --blank-translated-english-fx
```

Los mapas actuales pertenecen al video trabajado en este repositorio. Para otro video o idioma, primero deben generarse nuevos mapas de traduccion dentro del workspace de `translations`.

### 4. Generar SRT TV-Safe

```powershell
.\.venv\Scripts\python.exe .\src\ass_to_tv_safe_srt.py `
  --input-ass ".\output\entrada-demo-A1B2C3\entrada.spa.ass" `
  --output-srt ".\output\entrada-demo-A1B2C3\entrada.spa.srt"
```

### 5. Normalizar Espanol

```powershell
.\.venv\Scripts\python.exe .\src\normalize_spanish_subtitles.py `
  --input-ass ".\output\entrada-demo-A1B2C3\entrada.spa.ass" `
  --input-srt ".\output\entrada-demo-A1B2C3\entrada.spa.srt" `
  --output-ass ".\output\entrada-demo-A1B2C3\entrada.spa.ass" `
  --output-srt ".\output\entrada-demo-A1B2C3\entrada.spa.srt" `
  --report ".\subtitle_work\entrada-demo-A1B2C3\spanish_normalization_report.json"
```

### 6. Remux Manual con Ambas Pistas

```powershell
mkvmerge --output ".\output\entrada-demo-A1B2C3\entrada.spa.mkv" `
  --default-track-flag <subtitle-track-id-1>:no `
  --default-track-flag <subtitle-track-id-2>:no `
  ".\input\entrada.mkv" `
  --language 0:spa `
  --track-name "0:Español LatAm" `
  --default-track-flag 0:no `
  ".\output\entrada-demo-A1B2C3\entrada.spa.ass" `
  --language 0:spa `
  --track-name "0:Español LatAm TV-safe" `
  --default-track-flag 0:yes `
  ".\output\entrada-demo-A1B2C3\entrada.spa.srt"
```

Los numeros en `--default-track-flag <id>:no` son los track IDs de mkvmerge para las pistas de subtitulos originales. Desactiva todas las pistas originales para que solo la pista espanola deseada quede como default. Verificalo con `mkvmerge -J`.

## Flujo con Skill y Agentes

La skill local vive en:

```text
.agents\skills\mkv-subtitle-agentic-translation\SKILL.md
```

Puedes invocarla desde Codex asi:

```text
[$mkv-subtitle-agentic-translation](C:\Development\Proyectos\Video\.agents\skills\mkv-subtitle-agentic-translation\SKILL.md) "input\entrada.mkv"
```

Con la skill, el agente principal debe coordinar subagentes para:

- inspeccionar el contenedor y elegir la pista fuente correcta;
- evitar pistas `Forced` o CC como fuente principal cuando existan pistas completas;
- decidir si la pista es ASS, SRT, VTT u otro formato;
- crear workspaces dedicados en `subtitle_work/<workspace-id>/`, `translations/<workspace-id>/` y `output/<workspace-id>/`;
- convertir SRT/VTT a ASS con `src\subtitle_text_to_ass.py` cuando haga falta;
- segmentar semanticamente dialogos, signos y canciones;
- traducir o aplicar mapas de traduccion disponibles;
- aplicar glosarios locales para nombres, lugares, facciones y rangos;
- revisar naturalidad en espanol latino;
- sanear mapas JSON antes de aplicarlos y rechazar texto corrupto restante;
- limpiar duplicados, puentes cortos y fragmentos repetidos en subtitulos generados;
- generar ASS, SRT TV-safe y MKV portable;
- validar pistas embebidas, default flags y ausencia de basura visual. Para comprobar ausencia de pistas `[Local]`, abrir o copiar solo el MKV, sin los `.ass`/`.srt` auxiliares del mismo `output\<workspace-id>`.

La skill describe el flujo objetivo para soportar mas casos que el script PowerShell fijo. El script actual sigue siendo reproducible para el release ya traducido; la skill es la ruta adecuada cuando el archivo, idioma, formato de subtitulo o indice de pista no coinciden con ese caso.

Skills locales disponibles:

- `mkv-subtitle-agentic-translation`: traduce una pista textual embebida de MKV a espanol LatAm y genera ASS/SRT/MKV.
- `video-subtitle-agentic-transcription`: transcribe audio local con WhisperX/Whisper y remuxea un MKV con subtitulos base.
- `video-voice-cleaner`: limpia y normaliza voz/audio en un video antes de una transcripcion opcional.

## Formato de Traducciones

Los JSON aceptan dos tipos de claves:

- Numero de linea ASS, por ejemplo:

```json
{
  "60": "Idols escolares."
}
```

- Grupo de cancion por estilo y tiempo, por ejemplo:

```json
{
  "StayEnglish|0:47:15.15|0:47:19.18": "Si pudiera sonreir y decir 'luego',"
}
```

El aplicador conserva tiempos, estilos, orden de eventos y tags ASS iniciales. Para canciones, vacia los efectos ingleses y agrega lineas espanolas limpias sincronizadas.

## Normalizacion de Espanol

Despues de generar el ASS y el SRT, el flujo ejecuta `src\normalize_spanish_subtitles.py` salvo que pases `-SkipSpanishNormalization`.

La normalizacion:

- usa el texto visible del ASS como base principal;
- conserva tiempos, estilos, capas y solapamientos;
- evita tocar eventos tecnicos, dibujos, romaji, kanji y FX;
- corrige patrones de mojibake o acentos danados que hayan sobrevivido al saneamiento de mapas;
- redistribuye texto cuando un subtitulo repite todo el anterior y agrega contenido nuevo;
- fusiona duplicados exactos extendiendo el tiempo del subtitulo anterior;
- elimina subtitulos cortos tipo puente que son mitad del anterior y mitad del siguiente, extendiendo el anterior para evitar huecos visuales;
- recorta fragmentos repetidos cuando el subtitulo anterior termina con el texto completo del actual;
- regenera el SRT TV-safe con el mismo texto visible normalizado para eventos equivalentes;
- escribe un reporte en `subtitle_work\<workspace-id>\spanish_normalization_report.json` con los cambios aplicados.

Puedes correr las pruebas unitarias con:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\init_python_env.ps1
.\.venv\Scripts\python.exe -m unittest discover -s .\src -p "test_*.py"
```

## Notas

- Los subtitulos `[Local]` no vienen del MKV: aparecen cuando el reproductor detecta `.ass` o `.srt` externos en la misma carpeta. Para revisar o copiar a USB, usa el MKV de `output\<workspace-id>\`. Si copias tambien los `.ass`/`.srt` auxiliares al mismo destino, algunos reproductores los listaran como pistas locales externas.
- `subtitle_work/` esta ignorado porque contiene subtitulos generados/intermedios.
- Los MKV estan ignorados para evitar subir archivos grandes al repositorio.
