# MKV Subtitle Translation to Spanish

Workflow reproducible para extraer una pista ASS en ingles desde un MKV, aplicar traducciones al espanol y crear una copia del MKV con subtitulos `Español LatAm` embebidos como pista predeterminada.

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
- `translations_*.json`: mapas de traduccion.
- `.gitignore`: excluye videos, subtitulos extraidos, caches y temporales.

El video fuente y el MKV final no se versionan. Deben estar localmente en la carpeta del proyecto.

## Uso Rapido

Coloca el MKV fuente en la carpeta del proyecto con el nombre esperado por defecto:

```text
Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].mkv
```

Luego ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File .\traducir_subs_mkv.ps1
```

El script hace lo siguiente:

1. Extrae la pista de subtitulos `0:3` a `subtitle_work\*.eng.ass`.
2. Aplica las traducciones desde los JSON.
3. Genera `subtitle_work\*.spa.ass`.
4. Crea un MKV nuevo con `mkvmerge`, sin recodificar video/audio.
5. Marca la pista espanola como `spa`, titulo `Español LatAm`, y `default`.

Salida por defecto:

```text
Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.mkv
```

## Uso con Otros Nombres

Puedes pasar rutas personalizadas:

```powershell
powershell -ExecutionPolicy Bypass -File .\traducir_subs_mkv.ps1 `
  -InputMkv ".\entrada.mkv" `
  -EnglishAss ".\subtitle_work\entrada.eng.ass" `
  -SpanishAss ".\subtitle_work\entrada.spa.ass" `
  -OutputMkv ".\entrada.spa.mkv"
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

- No abras el `.spa.ass` junto al MKV final en la misma carpeta si no quieres que el reproductor lo cargue como pista externa `[Local]`.
- `subtitle_work/` esta ignorado porque contiene subtitulos generados/intermedios.
- Los MKV estan ignorados para evitar subir archivos grandes al repositorio.
