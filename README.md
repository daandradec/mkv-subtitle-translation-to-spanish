# Herramientas de video y subtítulos

Toolkit local en Python 3.12 y PowerShell para:

- traducir pistas de subtítulos MKV a español latinoamericano;
- transcribir audio y crear un MKV con subtítulos sincronizados;
- transcribir video a archivos de texto para RAG.

Los launchers canónicos viven en `src/<workflow>/`; el código reutilizable está en `src/shared/` y las instrucciones para agentes en `.agents/skills/`.

## Requisitos

- Windows PowerShell 5.1 o PowerShell 7;
- Python 3.12;
- `ffmpeg` y `ffprobe` en `PATH`;
- `mkvmerge` de MKVToolNix en `PATH` para los flujos que generan o traducen MKV;
- GPU CUDA opcional para acelerar WhisperX/Whisper.

Inicialización del entorno:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\shared\powershell\init_python_env.ps1
```

Pruebas completas:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\shared\powershell\run_tests.ps1
```

## Contrato de salida

Todos los workflows usan el nombre completo del archivo de entrada sin extensión:

```text
input/Mi video.mp4
└── output/Mi video/
```

No se agregan hashes, códigos aleatorios ni identificadores personalizados. En una ejecución nueva:

1. se comprueba que `output/<stem>/` sea un hijo directo de `output/`;
2. se rechaza la limpieza si el destino o alguno de sus descendientes es un reparse point;
3. se elimina todo el contenido previo del directorio determinista;
4. se crea el nuevo manifiesto y se generan los artefactos.

`-DryRun` nunca limpia el destino. En traducción, `-Resume` conserva el checkpoint y los mapas existentes; una ejecución sin `-Resume` siempre empieza limpia.

Estructura general:

```text
output/<stem>/
├── <entregables finales>
├── sidecars/                         # ASS/SRT solicitados como archivos
└── debug/
    └── <workflow>/
        ├── run_manifest.json
        ├── audio|source|backend|work/
        ├── postprocess|translations/
        └── reports|checkpoints|samples/
```

Las carpetas raíz históricas `subtitle_work/`, `translations/` y `tools/` ya no forman parte del runtime. Los datos heredados conservados durante esta migración están en `output/_legacy/debug/`; `_legacy` es un nombre reservado que los launchers nunca pueden limpiar. En modo carpeta, los launchers rechazan antes de procesar dos archivos que tengan el mismo stem, porque ambos apuntarían al mismo destino.

## Traducir subtítulos de un MKV

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\mkv-subtitle-agentic-translation\traducir_subs_mkv.ps1 `
  -InputMkv ".\input\video.mkv"
```

El flujo selecciona una pista textual compatible, la convierte a ASS cuando hace falta y busca mapas en:

```text
output/<stem>/debug/mkv-subtitle-agentic-translation/translations/<idioma>/
```

Si faltan mapas, conserva la extracción, escribe:

```text
output/<stem>/debug/mkv-subtitle-agentic-translation/checkpoints/translation_checkpoint.json
```

y termina con `[CHECKPOINT:AWAITING_TRANSLATION_MAPS]`. Después de crear `translations_all.json` o archivos `translations_*.json` en la ruta indicada, debe ejecutarse el comando guardado en el checkpoint. Ese comando incluye `-Resume` y las pistas exactas; no se debe iniciar una ejecución nueva porque limpiaría el checkpoint.

Salida típica:

```text
output/<stem>/<stem>.spa.mkv
output/<stem>/debug/mkv-subtitle-agentic-translation/subtitles/source/<stem>.source.ass
output/<stem>/debug/mkv-subtitle-agentic-translation/subtitles/generated/<stem>.spa.ass
output/<stem>/debug/mkv-subtitle-agentic-translation/subtitles/generated/<stem>.spa.srt
output/<stem>/debug/mkv-subtitle-agentic-translation/translations/<idioma>/...
output/<stem>/debug/mkv-subtitle-agentic-translation/reports/...
```

La raíz contiene únicamente el MKV final y la carpeta `debug`; este flujo no publica ASS/SRT externos. Las pistas originales se conservan como no predeterminadas. Cuando se generan ambas variantes, la pista `Español LatAm` ASS queda primera y predeterminada, seguida por la alternativa `Español LatAm TV-safe` SRT como no predeterminada. El launcher comprueba este contrato después del remux y escribe `reports/remux_validation_report.json`.

## Transcribir audio e incrustar subtítulos

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-subtitle-agentic-transcription\transcribe_video_audio.ps1 `
  -InputVideo ".\input\video.mp4"
```

WhisperX es el backend preferido y `openai-whisper` es el fallback local. La transcripción se mantiene en el idioma hablado; este workflow no traduce.

Para contenedores no Matroska, audio, video y SRT entran juntos a una sola operación FFmpeg. Así cualquier normalización dinámica de edit lists o preroll afecta por igual a todos los streams y no se aplica un retraso fijo.

Por defecto sólo se publica el MKV:

```text
output/<stem>/<stem>.transcribed.mkv
```

Para exportar también un ASS sincronizado con la pista ya incrustada:

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-subtitle-agentic-transcription\transcribe_video_audio.ps1 `
  -InputVideo ".\input\video.mp4" `
  --export-ass-file-subtitles
```

El ASS se extrae de la pista normalizada del MKV final y queda en:

```text
output/<stem>/sidecars/<stem>.transcribed.ass
```

Los archivos internos quedan en:

```text
output/<stem>/debug/video-subtitle-agentic-transcription/audio/
output/<stem>/debug/video-subtitle-agentic-transcription/whisper/
output/<stem>/debug/video-subtitle-agentic-transcription/postprocess/
output/<stem>/debug/video-subtitle-agentic-transcription/reports/
```

## Transcribir a texto

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-text-agent-transcription\transcribe_video_text.ps1 `
  -InputPath ".\input\video.mp4" `
  -Language es
```

`-InputPath` acepta un archivo o una carpeta no recursiva. Para el flujo agentic se confirma el idioma antes de la transcripción definitiva.

Salida:

```text
output/<stem>/<stem>.srt
output/<stem>/<stem>.md
output/<stem>/debug/video-text-agent-transcription/whisper/raw/<stem>.json
output/<stem>/debug/video-text-agent-transcription/whisper/raw/<stem>.srt
output/<stem>/debug/video-text-agent-transcription/whisper/raw/<stem>.vtt
output/<stem>/debug/video-text-agent-transcription/whisper/raw/<stem>.txt
output/<stem>/debug/video-text-agent-transcription/whisper/raw/<stem>.tsv
output/<stem>/debug/video-text-agent-transcription/whisper/postprocess/<stem>.vtt
output/<stem>/debug/video-text-agent-transcription/whisper/postprocess/<stem>.txt
output/<stem>/debug/video-text-agent-transcription/reports/text_transcription_report.json
```

## Desarrollo

- Python compatible con 3.12, cuatro espacios y nombres `snake_case`.
- Parámetros PowerShell descriptivos en PascalCase.
- Rutas con `pathlib.Path` en Python y `-LiteralPath` en operaciones destructivas de PowerShell.
- Pruebas en `src/shared/tests/` o `src/<workflow>/tests/`, sin depender de medios reales.
- Videos, modelos, outputs y mapas privados permanecen fuera de Git.
