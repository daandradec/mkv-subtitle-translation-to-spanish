# PRD: Text Transcription v0.0.2 - Timestamps por parrafo

## Resumen

Actualizar el postproceso de `video-generate-whisper-transcription` para que, despues de generar los archivos nativos de WhisperX/Whisper y las salidas limpias, el Markdown final use timestamps por parrafo en lugar de secciones fijas de aproximadamente 3 minutos.

El objetivo es que el Markdown sea mas util como base de conocimiento: cada idea o bloque textual tendra una referencia temporal mas precisa sin poner timestamps en cada frase.

## Cambio funcional

- Mantener la generacion inicial actual de JSON, SRT, VTT, TXT y Markdown.
- Agregar una fase posterior que lea el SRT limpio como fuente de tiempos.
- Reescribir el Markdown para reemplazar los headings temporales fijos por headings por parrafo:

```md
## 00:06:09 - 00:06:13

Parrafo 1...

## 00:06:13 - 00:07:08

Parrafo 2...
```

- Cada parrafo del Markdown debe recibir un rango temporal calculado desde los cues del SRT que componen ese parrafo.
- El proceso no debe relanzar WhisperX/Whisper ni modificar audio/video.

## Reglas

- Conservar frontmatter y titulo H1 del Markdown.
- Eliminar las secciones fijas de `-SectionSeconds` en el Markdown final.
- Usar el SRT limpio/canonico como fuente principal de tiempos.
- Mantener el texto ya normalizado del Markdown, no volver al texto crudo del backend.
- Si no se puede alinear un parrafo con alta confianza, usar el rango disponible mas cercano y registrar advertencia en el reporte.
- Mantener correcciones de encoding, lexico, sintaxis y semantica ya aplicadas por el postproceso.

## Ejemplo

Antes, una seccion de 3 minutos podia contener 7 parrafos bajo un solo timestamp:

```md
## 00:06:09 - 00:09:10

Parrafo 1...

Parrafo 2...
```

Despues, cada parrafo debe tener su propio heading temporal:

```md
## 00:06:09 - 00:06:13

Parrafo 1...

## 00:06:13 - 00:07:08

Parrafo 2...
```

## Validacion

- Verificar que el numero de parrafos utiles del Markdown se mantenga.
- Verificar que los rangos de tiempo sean monotonicamente crecientes.
- Verificar que el ultimo timestamp no exceda el ultimo cue del SRT.
- Revisar manualmente una muestra de inicio, mitad y final.
- Confirmar que no se relanza transcripcion.

## Supuestos

- El SRT canonico ya fue limpiado por `text_transcription_postprocess.py`.
- El Markdown y el SRT corresponden al mismo video y workspace.
- La granularidad deseada es parrafo, no frase ni cue individual.
