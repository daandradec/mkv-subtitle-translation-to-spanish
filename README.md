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
- `src\subtitle_workspace.py`: crea carpetas dedicadas por ejecucion para `subtitle_work/`, `translations/` y `output/`.
- `src\translation_maps.py`: resuelve mapas JSON por workspace e idioma fuente.
- `src\translation_terms.py`: aplica glosarios locales para normalizar nombres propios y terminos recurrentes.
- `src\test_*.py`: pruebas unitarias.
- `translations\`: mapas de traduccion locales. Esta carpeta esta ignorada por Git y no se sube al repositorio. Todos los idiomas, incluido ingles, usan `translations\<workspace-id>\<idioma>\`.
- `.gitignore`: excluye videos, subtitulos extraidos, caches y temporales.

El video fuente y el MKV final no se versionan. Por defecto, coloca entradas en `input/` y revisa resultados en `output/`.

Validaciones de entrada:

- Si `input/` no contiene ningun MKV y no indicas `-InputMkv`, el flujo se detiene. Un archivo de video `.mkv` con subtitulos incrustados es obligatorio para ejecutar la traduccion.
- Si `input/` contiene varios MKV, el flujo no elige automaticamente. Debes indicar exactamente un archivo con `-InputMkv`.
- Si el MKV seleccionado no tiene subtitulos incrustados, el flujo se detiene y avisa que no se encontraron subtitulos en el archivo original para traducir a espanol.
- `input/` es la carpeta canonica. Si escribes `inputs\archivo.mkv`, corrige a `input\archivo.mkv` cuando ese archivo exista.

Cada ejecucion crea workspaces dedicados para no mezclar artefactos de distintos videos:

```text
subtitle_work\<prefijo-24>-<codigo-6>\
translations\<prefijo-24>-<codigo-6>\
output\<prefijo-24>-<codigo-6>\
```

El prefijo se arma con palabras completas del nombre del MKV, hasta 24 caracteres, y el mismo identificador se usa en `subtitle_work`, `translations` y `output`.

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

1. Valida el MKV de entrada y selecciona la mejor pista textual soportada cuando no indicas `-SourceSubtitleStreamIndex`.
2. Crea un workspace dedicado en `subtitle_work\<workspace-id>\`, `translations\<workspace-id>\` y `output\<workspace-id>\`.
3. Extrae la pista de subtitulos seleccionada a `subtitle_work\<workspace-id>\*.source.ass`.
4. Aplica las traducciones desde los JSON y, si se pasan, glosarios con `-TermMapJson`.
5. Genera `output\<workspace-id>\*.spa.ass`.
6. Genera `output\<workspace-id>\*.spa.srt` cuando pasas `-TvSafeSrt`.
7. Normaliza el espanol visible del ASS y regenera el SRT TV-safe desde ese ASS normalizado.
8. Crea un MKV nuevo con `mkvmerge`, sin recodificar video/audio. Usa `-EmbeddedSubtitleFormat both` para incrustar ASS y SRT, `srt` para solo TV-safe, o `ass` para solo ASS estilizado.
9. Conserva las pistas originales pero desactiva el default en todos los subtitulos originales. La pista `Español LatAm TV-safe` queda como `spa` y `default`; `Español LatAm` ASS queda incrustada como alternativa no-default.

Salida por defecto:

```text
output\<workspace-id>\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.mkv
output\<workspace-id>\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.ass
output\<workspace-id>\Love Live! Nijigasaki High School Idol Club the Movie - Chapter 2 [BD 1080p HEVC OPUS] [34C012E9].spa.srt
```

Este flujo actual esta preparado para el caso ya trabajado y tambien puede seleccionar automaticamente una pista textual soportada cuando no se pasa indice. Para otros idiomas, mapas nuevos o subtitulos SRT/VTT incrustados, usa primero la inspeccion con agentes o los scripts auxiliares descritos abajo.

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

La seleccion automatica evita pistas `Forced` cuando hay pistas completas, evita CC/SDH salvo que se indique, prefiere mayor cobertura de eventos/duracion y considera la metadata del audio. Si quieres forzar otra pista, pasa `-SourceSubtitleStreamIndex` y, cuando el track ID de mkvmerge sea distinto, `-SourceMkvTrackId`:

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
python .\src\subtitle_language.py --input-mkv ".\input\entrada.mkv" --list-candidates
python .\src\subtitle_workspace.py --input-mkv ".\input\entrada.mkv" --workspace-id "entrada-demo-A1B2C3"
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
python .\src\subtitle_text_to_ass.py `
  --input ".\subtitle_work\entrada-demo-A1B2C3\entrada.source.srt" `
  --output ".\subtitle_work\entrada-demo-A1B2C3\entrada.source.ass"
```

Para VTT:

```powershell
python .\src\subtitle_text_to_ass.py `
  --input ".\subtitle_work\entrada-demo-A1B2C3\entrada.source.vtt" `
  --output ".\subtitle_work\entrada-demo-A1B2C3\entrada.source.ass" `
  --format vtt
```

Este modulo preserva tiempos, limpia marcas comunes de SRT/VTT y genera eventos `Dialogue:` con estilo `Default`. Su objetivo es que una pista de texto no-ASS pueda ser tratada por etapas posteriores como si ya fuera ASS. No hace traduccion por si mismo.

### 3. Aplicar Mapas de Traduccion

```powershell
python .\src\ass_apply_translations.py `
  --input-ass ".\subtitle_work\entrada-demo-A1B2C3\entrada.source.ass" `
  --output-ass ".\output\entrada-demo-A1B2C3\entrada.spa.ass" `
  --translations .\translations\entrada-demo-A1B2C3\ja\translations_all.json `
  --term-map .\translations\entrada-demo-A1B2C3\ja\term_map.json `
  --blank-translated-english-fx
```

Los mapas actuales pertenecen al video trabajado en este repositorio. Para otro video o idioma, primero deben generarse nuevos mapas de traduccion dentro del workspace de `translations`.

### 4. Generar SRT TV-Safe

```powershell
python .\src\ass_to_tv_safe_srt.py `
  --input-ass ".\output\entrada-demo-A1B2C3\entrada.spa.ass" `
  --output-srt ".\output\entrada-demo-A1B2C3\entrada.spa.srt"
```

### 5. Normalizar Espanol

```powershell
python .\src\normalize_spanish_subtitles.py `
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
- generar ASS, SRT TV-safe y MKV portable;
- validar pistas embebidas, default flags y ausencia de basura visual. Para comprobar ausencia de pistas `[Local]`, abrir o copiar solo el MKV, sin los `.ass`/`.srt` auxiliares del mismo `output\<workspace-id>`.

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
- escribe un reporte en `subtitle_work\<workspace-id>\spanish_normalization_report.json`.

Puedes correr las pruebas unitarias con:

```powershell
python -m unittest .\src\test_spanish_normalization.py .\src\test_language_profiles.py .\src\test_subtitle_text_to_ass.py .\src\test_workspace_and_terms.py
```

## Notas

- Los subtitulos `[Local]` no vienen del MKV: aparecen cuando el reproductor detecta `.ass` o `.srt` externos en la misma carpeta. Para revisar o copiar a USB, usa el MKV de `output\<workspace-id>\`. Si copias tambien los `.ass`/`.srt` auxiliares al mismo destino, algunos reproductores los listaran como pistas locales externas.
- `subtitle_work/` esta ignorado porque contiene subtitulos generados/intermedios.
- Los MKV estan ignorados para evitar subir archivos grandes al repositorio.
