# PRD: Normalización Agéntica de Español para Subtítulos ASS y TV-Safe

## Objetivo

Agregar una fase posterior a la generación actual del MKV final para normalizar el español de salida usando como entradas las dos pistas generadas:

- `outputs/*.spa.ass`, correspondiente a `Español LatAm [spa] (ass)`.
- `outputs/*.spa.srt`, correspondiente a `Español LatAm TV-safe [spa] (subrip)`.

La fase debe producir subtítulos en español latino más naturales, coherentes y respetuosos con el tono de la obra. Al finalizar, ambas pistas españolas deben compartir exactamente el mismo contenido textual normalizado, conservando cada una su propósito técnico: ASS para fidelidad general y SRT/SubRip para compatibilidad TV-safe.

## Contexto

El flujo actual ya genera:

1. Una pista `Español LatAm [spa] (ass)` con buen nivel de naturalidad y estilos ASS.
2. Una pista `Español LatAm TV-safe [spa] (subrip)` pensada para televisores y reproductores que renderizan mal ASS complejo.
3. Un MKV portable en `outputs/portable` con ambas pistas incrustadas.

Durante la revisión manual se detectó que los subtítulos principales ubicados en la parte inferior central no siempre tienen el mismo texto entre ASS y SRT. En algunos casos la versión ASS es más natural; en otros, la versión TV-safe puede contener diferencias que no conviene conservar. La nueva fase debe analizar ambas pistas y generar una versión textual unificada y mejorada.

## Problema

Hoy el ASS y el SRT TV-safe pueden divergir porque nacen de procesos técnicos distintos:

- El ASS conserva estructura, estilos, signos, capas y eventos especiales.
- El SRT TV-safe filtra efectos, dibujos vectoriales y comandos ASS para evitar basura visual en TV.
- La generación SRT puede omitir, simplificar o conservar texto distinto al ASS en ciertos rangos.

Esto puede producir dos experiencias lingüísticas diferentes para el usuario, aun cuando ambas pistas dicen representar el mismo español latino.

## Requisitos Funcionales

1. Momento de ejecución:
   - La normalización se ejecuta solo después de concluir la generación actual del MKV, el ASS español y el SRT TV-safe.
   - No reemplaza las fases de extracción, traducción inicial, generación ASS, generación SRT ni remux inicial.
   - Actúa como una fase de postprocesamiento lingüístico y de sincronización textual.

2. Entradas:
   - Leer estructuralmente el ASS español generado.
   - Leer estructuralmente el SRT TV-safe generado.
   - Extraer texto visible, tiempos, estilos, capas, efectos, posiciones y relaciones de solapamiento relevantes.
   - Usar ambas pistas como evidencia, pero considerar la pista `Español LatAm [spa] (ass)` como base principal de naturalidad cuando haya conflicto textual.

3. Salidas:
   - Generar un ASS español normalizado que preserve tiempos, estilos, capas y comportamiento actual.
   - Generar un SRT TV-safe normalizado con el mismo contenido textual que el ASS normalizado cuando representen el mismo evento visible.
   - Regenerar el MKV de `outputs/portable` con:
     - pista inglesa original ASS;
     - pista `Español LatAm [spa] (ass)`;
     - pista `Español LatAm TV-safe [spa] (subrip)` como default.

4. Igualdad textual:
   - Para los eventos equivalentes entre ASS y SRT, el contenido textual final debe ser idéntico.
   - La igualdad textual se compara después de remover tags ASS, normalizar saltos de línea y limpiar espacios.
   - No se exige igualdad textual para eventos que existen solo por una necesidad técnica de ASS, como dibujos, máscaras, efectos, karaoke visual o capas sin texto visible.

5. Naturalidad y tono:
   - El texto final debe sonar natural en español latino neutral.
   - Debe ser respetuoso, gentil y acorde al contenido emocional de la obra.
   - Debe evitar traducciones rígidas, literales o poco idiomáticas.
   - Debe conservar nombres, honoríficos y términos propios cuando aporten al tono de fandom o al contexto.
   - Debe mantener una longitud viable para subtítulos, evitando frases demasiado largas para el tiempo disponible.

6. Comportamiento que no debe cambiar:
   - No modificar tiempos de inicio o fin salvo que una validación futura lo justifique explícitamente.
   - No modificar el comportamiento actual de múltiples subtítulos simultáneos en el mismo rango de tiempo.
   - No colapsar diálogos con letras de canciones cuando hoy aparecen al mismo tiempo.
   - No eliminar la coexistencia correcta de canción, diálogo, signos o texto en pantalla cuando el comportamiento actual sea intencional.
   - No convertir eventos técnicos ASS en texto visible.

7. Canciones:
   - Mantener el comportamiento actual donde pueden coexistir letras de canción y diálogo.
   - Usar reconstrucción semántica de letras completas para revisar naturalidad.
   - Si una línea musical no puede normalizarse con confianza, conservar la versión más segura o dejarla fuera del TV-safe, según las reglas existentes.
   - Nunca introducir comandos ASS, rutas vectoriales, placeholders o caracteres repetidos como texto visible.

## Flujo Agéntico Propuesto

El agente principal coordina subagentes y conserva la responsabilidad de integración, remux y validación final.

1. Inspector de subtítulos generados:
   - Lee ASS y SRT finales.
   - Produce un inventario de eventos visibles, tiempos, estilos, capas y texto normalizado.
   - Detecta equivalencias entre eventos ASS y cues SRT.

2. Alineador textual ASS/SRT:
   - Empareja eventos por tiempo, texto visible, estilo y contexto.
   - Clasifica diferencias como equivalentes, divergentes, solo ASS, solo SRT o técnicas.
   - Marca casos de solapamiento intencional para no colapsarlos.

3. Revisor lingüístico español LatAm:
   - Propone una versión normalizada para cada unidad textual.
   - Usa el ASS como base preferente cuando haya conflicto.
   - Puede tomar mejoras del SRT si su redacción es más natural.
   - Aplica criterio propio de naturalidad, respeto, gentileza y coherencia narrativa.

4. Revisor de canciones y solapamientos:
   - Revisa canciones, letras reconstruidas y rangos donde coinciden canción y diálogo.
   - Verifica que no se altere el comportamiento de múltiples subtítulos simultáneos.
   - Confirma que las letras TV-safe no tengan residuos visuales ni efectos.

5. Validador técnico:
   - Verifica igualdad textual entre ASS normalizado y SRT normalizado para eventos equivalentes.
   - Extrae la pista final desde el MKV portable.
   - Escanea basura visible: tags ASS, dibujos, comandos, rutas vectoriales, placeholders, caracteres repetidos o números sin sentido.
   - Valida metadatos, pistas, default flags y ausencia de subtítulos `[Local]` en `outputs/portable`.

## Estrategia de Implementación

1. Crear un modelo intermedio de subtítulos:
   - `subtitle_id`
   - `source_format`
   - `start`
   - `end`
   - `style`
   - `layer`
   - `effect`
   - `visible_text`
   - `technical_tags`
   - `is_song`
   - `is_dialogue`
   - `is_sign`
   - `is_technical_only`
   - `overlap_group_id`
   - `equivalence_group_id`

2. Construir grupos de equivalencia:
   - Agrupar por ventanas temporales exactas o cercanas.
   - Comparar texto visible y contexto.
   - Mantener grupos separados cuando haya solapamiento intencional entre canción, diálogo y signos.

3. Normalizar texto por grupo:
   - Usar ASS como candidato principal.
   - Comparar SRT como candidato secundario.
   - Producir `normalized_text`.
   - Registrar razón de cambio cuando difiera del ASS o del SRT.

4. Reaplicar normalización:
   - En ASS: reemplazar solo texto visible seguro, preservando tags iniciales, estilo, layer, márgenes, efectos y tiempos.
   - En SRT: escribir cues TV-safe con el mismo `normalized_text` para grupos equivalentes.
   - No crear texto para eventos técnicos o no visibles.

5. Regenerar MKV portable:
   - Remuxear el MKV con ASS y SRT normalizados.
   - Mantener la pista `Español LatAm TV-safe` como default.
   - Mantener la pista `Español LatAm` ASS como alternativa incrustada.

## Reglas de Decisión

- Si ASS y SRT difieren y ASS es natural: usar ASS.
- Si ASS y SRT difieren y SRT es más natural: usar SRT como base, pero validar contra contexto.
- Si ambos son mejorables: crear una tercera versión normalizada.
- Si una unidad es técnica, dibujo, máscara, karaoke visual o placeholder: no generar texto visible.
- Si una línea coincide temporalmente con otra pero representa una función distinta, como canción y diálogo: no fusionar.
- Si una línea normalizada rompe lectura por duración, acortarla sin perder significado central.

## Validación

1. Validación textual:
   - Eventos equivalentes ASS/SRT tienen el mismo texto visible normalizado.
   - No hay divergencias no justificadas en subtítulos principales inferiores.
   - Los cambios lingüísticos mejoran naturalidad sin alterar significado.

2. Validación técnica:
   - ASS conserva tiempos, estilos, capas y tags necesarios.
   - SRT conserva formato SubRip válido.
   - MKV final contiene las pistas esperadas:
     - `eng` ASS original no-default;
     - `spa` ASS `Español LatAm` no-default;
     - `spa` SubRip `Español LatAm TV-safe` default.
   - `outputs/portable` no contiene `.ass` ni `.srt` junto al MKV final.

3. Escaneo anti-basura:
   - Sin `{...}` visible.
   - Sin `\pos`, `\move`, `\fad`, `\p`, karaoke tags ni comandos ASS visibles.
   - Sin rutas vectoriales `m`, `l`, `b` con números.
   - Sin placeholders de caracteres repetidos como `ffffffff`.
   - Sin líneas compuestas mayoritariamente por números sin sentido.

4. Validación manual recomendada:
   - Inicio del video.
   - Una escena de diálogo normal.
   - Una escena con texto en pantalla.
   - Canciones con diálogo simultáneo.
   - Rango `00:44:30` a `00:45:49`.
   - Rango donde se detectó `ffffffff` alrededor de `00:50:57`.
   - Ending y créditos.

## Tests Esperados

- Parser ASS preserva estructura y reemplaza solo texto visible.
- Parser SRT lee y escribe cues válidos.
- Alineador no fusiona solapamientos de canción y diálogo.
- Normalizador produce el mismo texto para eventos equivalentes ASS/SRT.
- Filtro TV-safe descarta comandos ASS, dibujos, placeholders y residuos de efectos.
- Remux final conserva las tres pistas esperadas y el default correcto.
- Extracción de pista embebida confirma texto normalizado legible.

## No Objetivos

- No rediseñar la traducción desde cero.
- No eliminar estilos ASS ni simplificar toda la pista ASS.
- No remover el soporte de subtítulos simultáneos.
- No cambiar la pista inglesa original.
- No borrar archivos generados durante la ejecución del flujo.
- No subir MKV, ASS, SRT ni artefactos pesados al repositorio.

## Criterios de Éxito

- El usuario puede ejecutar el flujo actual y luego la fase de normalización.
- El MKV final en `outputs/portable` contiene ASS y SRT españoles normalizados.
- Los subtítulos principales equivalentes dicen lo mismo en ASS y TV-safe.
- La redacción se siente natural, respetuosa y coherente con la obra.
- El comportamiento actual de canciones, diálogos simultáneos y signos se preserva.
- La pista TV-safe no muestra basura visual en TV.
