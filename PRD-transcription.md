# PRD: Transcripcion Agentica de Subtitulos de Video

## Resumen

Crear la skill local `video-generate-new-subtitles-from-audio` para procesar videos sin subtitulos incorporados. El flujo transcribe el audio en su idioma original, genera subtitulos base y convierte/remuxea el video a un MKV nuevo con una pista de subtitulos incrustada. Ese MKV queda listo para usarse despues con `video-generate-traslated-subtitles-from-existing-subtitles`.

El backend preferido es WhisperX por sus timestamps/alineacion, VAD y procesamiento por lotes. Si WhisperX no queda disponible dentro del entorno virtual local, el flujo usa `openai-whisper` como fallback desde ese mismo entorno. v1 no incluye diarizacion ni requiere API keys.

El proyecto debe ejecutar los flujos desde un entorno virtual local `.venv/` creado con Python 3.12. No debe depender del Python global del usuario, porque WhisperX publicado en PyPI requiere Python `>=3.10,<3.14` y falla con Python 3.14.

Fuentes consideradas: OpenAI Whisper (`https://github.com/openai/whisper`), WhisperX (`https://github.com/m-bain/whisperX`) y faster-whisper (`https://github.com/SYSTRAN/faster-whisper`).

## Requisitos Funcionales

- Inicializar y activar `.venv/` con Python 3.12 antes de cualquier flujo.
- Instalar dependencias requeridas desde `requirements.txt` dentro de `.venv/`, no en Python global.
- Intentar instalar WhisperX desde `requirements-whisperx.txt` como backend preferido; si falla, continuar con `openai-whisper` cuando este disponible.
- Aceptar un video en `input/` o una ruta explicita con `-InputVideo`.
- Permitir cualquier archivo de video con audio decodificable por FFmpeg/Whisper; ejemplos comunes: MKV, MP4, MOV, M4V, WebM, AVI, WMV, FLV, TS/M2TS, MPEG/MPG, 3GP/3G2 y OGV.
- Procesar solo un video por ejecucion.
- Seleccionar el audio default o permitir override con `-AudioStreamIndex`.
- Extraer audio a WAV mono 16 kHz reproducible en `output/<stem>/debug/video-generate-new-subtitles-from-audio/audio/`.
- Transcribir al idioma original:
  - usar WhisperX cuando este disponible;
  - usar `openai-whisper` si WhisperX no existe;
  - permitir `-Language`, pero si falta dejar que el backend detecte idioma.
- Generar `output/<stem>/<stem>.transcribed.mkv` como entregable predeterminado.
- Generar opcionalmente `output/<stem>/sidecars/<stem>.transcribed.ass` con `--export-ass-file-subtitles`, extrayéndolo del MKV ya normalizado.
- Escribir reportes en `output/<stem>/debug/video-generate-new-subtitles-from-audio/reports/`.
- Incrustar la pista SRT transcrita en un MKV final con `mkvmerge`, sin recodificar video/audio cuando el contenedor permita copy remux.
- Mantener pistas originales y marcar la pista transcrita como default.
- Avisar si el idioma detectado no esta dentro de los idiomas soportados por la skill de traduccion.

## Flujo

1. Validar Python 3.12 y crear/activar `.venv/`.
2. Instalar o actualizar dependencias cuando cambie `requirements.txt` o `requirements-whisperx.txt`.
3. Validar `input/`, archivo de video, FFmpeg, FFprobe y MKVToolNix.
4. Limpiar de forma segura y crear el destino determinista `output/<stem>/`, sin hash ni identificador personalizado.
5. Inspeccionar audio con `ffprobe` y seleccionar la pista adecuada.
6. Extraer audio con:

```powershell
ffmpeg -y -v error -i "<input-video>" -map "0:<audio_index>" -vn -ac 1 -ar 16000 -c:a pcm_s16le "<workspace>.audio.wav"
```

7. Ejecutar backend desde `.venv\Scripts`:
   - WhisperX:

```powershell
whisperx "<audio.wav>" --model large-v3 --device cuda --compute_type float16 --batch_size 8 --output_dir "<workdir>" --output_format all
```

   - Fallback Whisper:

```powershell
whisper "<audio.wav>" --model turbo --task transcribe --device cuda --fp16 True --output_dir "<workdir>" --output_format all
```

8. Postprocesar el SRT generado: limpiar cues vacios y validar tiempos; conservarlo sólo como entrada interna bajo `debug/`.
9. Remuxear Matroska/WebM con `mkvmerge`. Para MP4/MOV y otros contenedores, mapear fuente y SRT juntos en una sola invocación FFmpeg para aplicar una transformación temporal uniforme y evitar offsets por edit lists/preroll.
10. Validar que el MKV final contenga la pista transcrita.

## Backend y Calidad

- Default WhisperX: `large-v3`, `cuda`, `float16`, `batch_size 8`.
- Default fallback Whisper: `turbo`, `cuda`, `fp16 True`.
- `openai-whisper` se instala automaticamente en `.venv/` desde `requirements.txt`.
- WhisperX se intenta instalar automaticamente en `.venv/` desde `requirements-whisperx.txt` como backend preferido, pero no bloquea el fallback si falla.
- Si Python 3.12 no esta instalado, el flujo se detiene con una instruccion clara para instalarlo.
- No se usa `--task translate`; la transcripcion conserva el idioma hablado.
- No se implementa diarizacion en v1.

## Compatibilidad con Traduccion

El MKV generado debe ser aceptado por `video-generate-traslated-subtitles-from-existing-subtitles`. Si la pista transcrita queda en SRT, la skill de traduccion debe poder extraerla y convertirla a ASS simple con el modulo compartido `video_toolkit.subtitles.text` antes de aplicar mapas de traduccion.

Si el idioma detectado no pertenece a los idiomas traducibles actuales, el MKV transcrito sigue siendo valido, pero la traduccion automatica posterior puede detenerse por idioma no soportado.

## Validacion

- Unit tests:
  - salida usa el stem completo y limpia sólo su directorio determinista;
  - seleccion de backend `auto`, fallback y error sin backend;
  - postproceso rechaza transcripciones vacias;
  - postproceso genera SRT interno limpio y reporte;
  - mapeo de idioma produce metadata MKV razonable y warnings para idiomas no traducibles.
- Script tests:
  - parse de `src/shared/powershell/init_python_env.ps1`;
  - parse de `src/video-generate-new-subtitles-from-audio/transcribe_video_audio.ps1`;
  - `py_compile` de modulos nuevos.
- Validacion manual:
  - MKV/MP4 sin subtitulos genera un MKV transcrito y ASS sidecar sólo cuando se solicita;
  - videos con varios audios permiten `-AudioStreamIndex`;
  - fallback Whisper muestra aviso cuando WhisperX no existe;
  - MKV transcrito se puede usar luego con la skill de traduccion.
