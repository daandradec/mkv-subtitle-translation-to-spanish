# MKV Subtitle Translation to Spanish

Workflow reproducible para extraer una pista ASS en ingles desde un MKV, aplicar traducciones al espanol y crear una copia del MKV con dos pistas espanolas embebidas: `Español LatAm` en ASS y `Español LatAm TV-safe` en SRT para reproductores o televisores que renderizan mal ASS complejo.

El repositorio contiene los scripts y mapas de traduccion. Los videos, subtitulos extraidos y archivos de trabajo pesados quedan ignorados por Git.

## Requisitos

- Windows PowerShell.
- Python 3 disponible como `python`.
- FFmpeg disponible en PATH:
  - `ffmpeg`
  - `ffprobe`
- MKVToolNix disponible en PATH:
  - `mkvmerge`

Instalacion sugerida con Chocolatey:

```powershell
choco install ffmpeg mkvtoolnix -y
```

Verifica:

```powershell
ffmpeg -version
ffprobe -version
mkvmerge --version
python --version
```

Si `mkvmerge` existe pero PowerShell no lo detecta, cierra y vuelve a abrir la terminal. En instalaciones manuales de MKVToolNix, agrega esta carpeta al PATH si aplica:

```powershell
C:\Program Files\MKVToolNix
```

## Archivos Principales

- `traducir_subs_mkv.ps1`: orquesta todo el flujo.
- `ass_apply_translations.py`: aplica las traducciones sobre el ASS sin cambiar tiempos.
- `ass_to_tv_safe_srt.py`: crea un SRT limpio sin tags ASS, dibujos vectoriales ni efectos karaoke.
- `translations_*.json`: mapas de traduccion.
- `.gitignore`: excluye videos, subtitulos extraidos, caches y temporales.

El video fuente y el MKV final no se versionan. Por defecto, coloca entradas en `input/` y revisa resultados en `output/`.

## Uso Rapido

Coloca el MKV fuente en `input/`:

```text
input\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].mkv
```

Luego ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File .\traducir_subs_mkv.ps1 `
  -InputMkv ".\input\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].mkv" `
  -SpanishAss ".\output\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.ass" `
  -TvSafeSrt ".\output\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.srt" `
  -EmbeddedSubtitleFormat both `
  -OutputMkv ".\output\portable\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.mkv"
```

El script hace lo siguiente:

1. Extrae la pista de subtitulos `0:3` a `subtitle_work\*.eng.ass`.
2. Aplica las traducciones desde los JSON.
3. Genera `output\*.spa.ass`.
4. Genera `output\*.spa.srt` cuando pasas `-TvSafeSrt`.
5. Crea un MKV nuevo con `mkvmerge`, sin recodificar video/audio. Usa `-EmbeddedSubtitleFormat both` para incrustar ASS y SRT, `srt` para solo TV-safe, o `ass` para solo ASS estilizado.
6. Marca `Español LatAm TV-safe` como `spa` y `default`; deja `Español LatAm` ASS incrustado como alternativa no-default.

Salida por defecto:

```text
output\portable\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.mkv
output\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.ass
output\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.srt
```

## Uso con Otros Nombres

Puedes pasar rutas personalizadas:

```powershell
powershell -ExecutionPolicy Bypass -File .\traducir_subs_mkv.ps1 `
  -InputMkv ".\entrada.mkv" `
  -EnglishAss ".\subtitle_work\entrada.eng.ass" `
  -SpanishAss ".\output\entrada.spa.ass" `
  -TvSafeSrt ".\output\entrada.spa.srt" `
  -EmbeddedSubtitleFormat both `
  -OutputMkv ".\output\portable\entrada.spa.mkv"
```

Si usas otro MKV, revisa primero el indice de la pista de subtitulos con:

```powershell
ffprobe -hide_banner -i ".\entrada.mkv"
```

El script actual extrae la pista `0:3`. Si tu archivo usa otra pista, cambia esta linea en `traducir_subs_mkv.ps1`:

```powershell
ffmpeg -y -v error -i $InputMkv -map 0:3 -c:s copy $EnglishAss
```

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

## Notas

- Los subtitulos `[Local]` no vienen del MKV: aparecen cuando el reproductor detecta `.ass` o `.srt` externos en la misma carpeta. Para revisar o copiar a USB, usa el MKV de `output\portable\`, que queda separado de esos archivos auxiliares.
- `subtitle_work/` esta ignorado porque contiene subtitulos generados/intermedios.
- Los MKV estan ignorados para evitar subir archivos grandes al repositorio.
