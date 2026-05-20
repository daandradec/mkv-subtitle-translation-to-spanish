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

- `src\traducir_subs_mkv.ps1`: orquesta todo el flujo.
- `src\ass_apply_translations.py`: aplica las traducciones sobre el ASS sin cambiar tiempos.
- `src\ass_to_tv_safe_srt.py`: crea un SRT limpio sin tags ASS, dibujos vectoriales ni efectos karaoke.
- `src\normalize_spanish_subtitles.py`: normaliza el texto visible del ASS y regenera el SRT TV-safe desde el ASS normalizado.
- `src\subtitle_text_to_ass.py`: convierte subtitulos extraidos `.srt`, `.vtt` o `.webvtt` a un ASS simple para que puedan entrar a etapas que esperan ASS.
- `src\subtitle_language.py` y `src\languages\`: validan que la pista fuente este en la lista de idiomas soportados.
- `src\test_*.py`: pruebas unitarias.
- `translations\translations_*.json`: mapas de traduccion locales. Esta carpeta esta ignorada por Git y no se sube al repositorio.
- `.gitignore`: excluye videos, subtitulos extraidos, caches y temporales.

El video fuente y el MKV final no se versionan. Por defecto, coloca entradas en `input/` y revisa resultados en `output/`.

Validaciones de entrada:

- Si `input/` no contiene ningun MKV y no indicas `-InputMkv`, el flujo se detiene. Un archivo de video `.mkv` con subtitulos incrustados es obligatorio para ejecutar la traduccion.
- Si `input/` contiene varios MKV, el flujo no elige automaticamente. Debes indicar exactamente un archivo con `-InputMkv`.
- Si el MKV seleccionado no tiene subtitulos incrustados, el flujo se detiene y avisa que no se encontraron subtitulos en el archivo original para traducir a espanol.

## Flujo Principal con PowerShell

Coloca el MKV fuente en `input/`:

```text
input\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].mkv
```

Luego ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\traducir_subs_mkv.ps1 `
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
5. Normaliza el espanol visible del ASS y regenera el SRT TV-safe desde ese ASS normalizado.
6. Crea un MKV nuevo con `mkvmerge`, sin recodificar video/audio. Usa `-EmbeddedSubtitleFormat both` para incrustar ASS y SRT, `srt` para solo TV-safe, o `ass` para solo ASS estilizado.
7. Marca `Español LatAm TV-safe` como `spa` y `default`; deja `Español LatAm` ASS incrustado como alternativa no-default.

Salida por defecto:

```text
output\portable\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.mkv
output\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.ass
output\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.srt
```

Este flujo actual esta preparado para el caso ya trabajado: MKV con pista ASS fuente en `0:3` y mapas de traduccion existentes. Para otros idiomas, otras pistas o subtitulos SRT/VTT incrustados, usa primero la inspeccion con agentes o los scripts auxiliares descritos abajo.

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

Si la metadata de la pista de subtitulos indica otro idioma, `src\traducir_subs_mkv.ps1` detiene la ejecucion y muestra la lista disponible. Para ingles se conserva el comportamiento actual con mapas locales en `translations\`. Para los otros idiomas soportados, la ruta recomendada es usar la skill con subagentes para generar mapas JSON locales en `translations\<video>\<idioma>\` y luego pasarlos al script con `-TranslationJson`.

## Uso con Otros Nombres

Puedes pasar rutas personalizadas:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\traducir_subs_mkv.ps1 `
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

El script actual extrae la pista `0:3` y desactiva el track `3` de mkvmerge por defecto. Si tu archivo usa otra pista, pasa `-SourceSubtitleStreamIndex` y, cuando el track ID de mkvmerge sea distinto, `-SourceMkvTrackId`:

```powershell
powershell -ExecutionPolicy Bypass -File .\src\traducir_subs_mkv.ps1 `
  -InputMkv ".\input\entrada.mkv" `
  -SourceSubtitleStreamIndex 4 `
  -SourceMkvTrackId 4
```

## Flujo por Scripts Python

Los scripts tambien pueden usarse por piezas cuando estas preparando o depurando una pista de subtitulos.

### 1. Extraer Subtitulos

Inspecciona el contenedor:

```powershell
ffprobe -hide_banner -i ".\input\entrada.mkv"
```

Extrae una pista ASS:

```powershell
ffmpeg -y -i ".\input\entrada.mkv" -map 0:3 -c:s copy ".\subtitle_work\entrada.ass"
```

Extrae una pista SRT o VTT si el contenedor la trae como texto:

```powershell
ffmpeg -y -i ".\input\entrada.mkv" -map 0:s:0 -c:s copy ".\subtitle_work\entrada.srt"
```

El indice real puede variar; usa el resultado de `ffprobe`.

### 2. Convertir SRT/VTT a ASS

Cuando la pista fuente extraida sea `.srt`, `.vtt` o `.webvtt`, conviertela a ASS simple:

```powershell
python .\src\subtitle_text_to_ass.py `
  --input ".\subtitle_work\entrada.srt" `
  --output ".\subtitle_work\entrada.ass"
```

Para VTT:

```powershell
python .\src\subtitle_text_to_ass.py `
  --input ".\subtitle_work\entrada.vtt" `
  --output ".\subtitle_work\entrada.ass" `
  --format vtt
```

Este modulo preserva tiempos, limpia marcas comunes de SRT/VTT y genera eventos `Dialogue:` con estilo `Default`. Su objetivo es que una pista de texto no-ASS pueda ser tratada por etapas posteriores como si ya fuera ASS. No hace traduccion por si mismo.

### 3. Aplicar Mapas de Traduccion

```powershell
python .\src\ass_apply_translations.py `
  --input-ass ".\subtitle_work\entrada.ass" `
  --output-ass ".\output\entrada.spa.ass" `
  --translations .\translations\translations_dialogue_part1.json .\translations\translations_dialogue_part2.json .\translations\translations_signs.json .\translations\translations_songs.json .\translations\translations_songs_extra.json `
  --blank-translated-english-fx
```

Los mapas actuales pertenecen al video trabajado en este repositorio. Para otro video o idioma, primero deben generarse nuevos mapas de traduccion.

### 4. Generar SRT TV-Safe

```powershell
python .\src\ass_to_tv_safe_srt.py `
  --input-ass ".\output\entrada.spa.ass" `
  --output-srt ".\output\entrada.spa.srt"
```

### 5. Normalizar Espanol

```powershell
python .\src\normalize_spanish_subtitles.py `
  --input-ass ".\output\entrada.spa.ass" `
  --input-srt ".\output\entrada.spa.srt" `
  --output-ass ".\output\entrada.spa.ass" `
  --output-srt ".\output\entrada.spa.srt" `
  --report ".\subtitle_work\spanish_normalization_report.json"
```

### 6. Remux Manual con Ambas Pistas

```powershell
mkvmerge --output ".\output\portable\entrada.spa.mkv" `
  --default-track-flag 3:no `
  ".\input\entrada.mkv" `
  --language 0:spa `
  --track-name "0:Español LatAm" `
  --default-track-flag 0:no `
  ".\output\entrada.spa.ass" `
  --language 0:spa `
  --track-name "0:Español LatAm TV-safe" `
  --default-track-flag 0:yes `
  ".\output\entrada.spa.srt"
```

El numero `3` en `--default-track-flag 3:no` es el track ID de mkvmerge para la pista de subtitulos original en este release. Verificalo con `mkvmerge -J`.

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
- decidir si la pista es ASS, SRT, VTT u otro formato;
- convertir SRT/VTT a ASS con `src\subtitle_text_to_ass.py` cuando haga falta;
- segmentar semanticamente dialogos, signos y canciones;
- traducir o aplicar mapas de traduccion disponibles;
- revisar naturalidad en espanol latino;
- generar ASS, SRT TV-safe y MKV portable;
- validar pistas, default flags, ausencia de basura visual y ausencia de subtitulos `[Local]` en `output\portable`.

La skill describe el flujo objetivo para soportar mas casos que el script PowerShell fijo. El script actual sigue siendo reproducible para el release ya traducido; la skill es la ruta adecuada cuando el archivo, idioma, formato de subtitulo o indice de pista no coinciden con ese caso.

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
- regenera el SRT TV-safe con el mismo texto visible normalizado para eventos equivalentes;
- escribe un reporte en `subtitle_work\spanish_normalization_report.json`.

Puedes correr las pruebas unitarias con:

```powershell
python -m unittest .\src\test_spanish_normalization.py .\src\test_language_profiles.py
```

## Notas

- Los subtitulos `[Local]` no vienen del MKV: aparecen cuando el reproductor detecta `.ass` o `.srt` externos en la misma carpeta. Para revisar o copiar a USB, usa el MKV de `output\portable\`, que queda separado de esos archivos auxiliares.
- `subtitle_work/` esta ignorado porque contiene subtitulos generados/intermedios.
- Los MKV estan ignorados para evitar subir archivos grandes al repositorio.
