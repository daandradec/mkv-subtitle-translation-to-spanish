# Herramientas de video, subtítulos y transcripción

Toolkit local para Windows, Python 3.12 y PowerShell que permite procesar videos sin depender de APIs externas. El repositorio cubre tres necesidades distintas:

- traducir al español latinoamericano una pista de subtítulos ya incrustada en un MKV;
- crear subtítulos nuevos desde el audio y entregarlos incrustados en un MKV sincronizado;
- generar transcripciones SRT y Markdown limpias, preparadas para revisión humana o ingestión RAG.

Los launchers canónicos viven en `src/<workflow>/`, el código reutilizable está en `src/shared/` y las instrucciones agentic están en `.agents/skills/<workflow>/`.

> **Importante:** el nombre canónico `video-generate-traslated-subtitles-from-existing-subtitles` usa `traslated` exactamente como fue aprobado. No debe corregirse a `translated` en comandos, rutas, imports o invocaciones de skill.

## Índice

- [Elegir el workflow correcto](#elegir-el-workflow-correcto)
- [Estado actual del proyecto](#estado-actual-del-proyecto)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Requisitos](#requisitos)
- [Convenciones de entrada](#convenciones-de-entrada)
- [Contrato de salida y limpieza segura](#contrato-de-salida-y-limpieza-segura)
- [Workflow 1: traducir subtítulos existentes](#workflow-1-traducir-subtítulos-existentes)
- [Workflow 2: crear subtítulos nuevos desde el audio](#workflow-2-crear-subtítulos-nuevos-desde-el-audio)
- [Workflow 3: generar transcripción Whisper para texto y RAG](#workflow-3-generar-transcripción-whisper-para-texto-y-rag)
- [Encadenar creación y traducción de subtítulos](#encadenar-creación-y-traducción-de-subtítulos)
- [Solución de problemas](#solución-de-problemas)
- [Validación manual recomendada](#validación-manual-recomendada)
- [Desarrollo](#desarrollo)

## Elegir el workflow correcto

| Necesidad | Workflow/skill | Entrada | Entregable público principal |
|---|---|---|---|
| El MKV ya contiene subtítulos de texto y deben traducirse a español LatAm | `video-generate-traslated-subtitles-from-existing-subtitles` | Un archivo `.mkv` con ASS, SRT, VTT o WebVTT incrustado | `<stem>.spa.mkv` |
| El video no tiene subtítulos utilizables y deben crearse desde las voces | `video-generate-new-subtitles-from-audio` | Un video con audio decodificable | `<stem>.transcribed.mkv` |
| Se necesita texto para RAG, búsqueda, documentación o análisis, sin crear otro MKV | `video-generate-whisper-transcription` | Un video o una carpeta de videos | `<stem>.srt` y `<stem>.md` |

Regla rápida:

1. Si el video ya tiene subtítulos de texto, usa el workflow de traducción.
2. Si no tiene subtítulos, pero quieres terminar con un MKV subtitulado, usa el workflow desde audio.
3. Si solo necesitas el contenido hablado como texto, usa el workflow de transcripción Whisper.
4. Si el objetivo final es un MKV traducido pero el original no tiene subtítulos, encadena primero `video-generate-new-subtitles-from-audio` y después `video-generate-traslated-subtitles-from-existing-subtitles`.

## Estado actual del proyecto

El toolkit consolida las siguientes decisiones y mejoras:

- entorno local único `.venv/` con Python 3.12;
- launchers PowerShell canónicos por subproyecto;
- paquetes Python aislados por workflow y módulos compartidos bajo `video_toolkit`;
- selección explícita o automática de pistas de audio y subtítulos mediante `ffprobe`;
- WhisperX como backend preferido y OpenAI Whisper como fallback completamente local;
- directorios de salida deterministas, sin hashes ni sufijos aleatorios;
- limpieza segura limitada al hijo directo `outputs/<stem>/`;
- checkpoints durables para preparar, traducir y reanudar un MKV sin perder mapas;
- normalización de español y salida TV-safe para evitar comandos ASS visibles;
- remux de MP4/MOV en una sola línea temporal para evitar offsets constantes;
- sidecars públicos únicamente cuando se solicitan de forma explícita;
- Markdown con timestamps por párrafo y frontmatter para RAG;
- pruebas de imports canónicos, límites de dependencias, workspaces, formatos, selección de idioma y remux.

Los nombres anteriores fueron reemplazados completamente:

| Nombre anterior | Nombre actual |
|---|---|
| `mkv-subtitle-agentic-translation` | `video-generate-traslated-subtitles-from-existing-subtitles` |
| `video-subtitle-agentic-transcription` | `video-generate-new-subtitles-from-audio` |
| `video-text-agent-transcription` | `video-generate-whisper-transcription` |
| `mkv_subtitle_agentic_translation` | `video_generate_traslated_subtitles_from_existing_subtitles` |
| `video_subtitle_agentic_transcription` | `video_generate_new_subtitles_from_audio` |
| `video_text_agent_transcription` | `video_generate_whisper_transcription` |

No existen aliases de compatibilidad para los nombres anteriores. Scripts externos, accesos directos o automatizaciones locales deben usar los nombres actuales.

## Estructura del repositorio

```text
.
├── .agents/
│   └── skills/
│       ├── video-generate-new-subtitles-from-audio/
│       ├── video-generate-traslated-subtitles-from-existing-subtitles/
│       └── video-generate-whisper-transcription/
├── .cache/                                  # cachés, modelos y paquetes Python regenerables
├── .tmp/                                    # temporales efímeros de build, pruebas y ejecución
├── .venv/                                   # entorno Python local persistente
├── inputs/                                  # medios de entrada locales
├── outputs/                                 # entregables y artefactos generados
├── scripts/                                # administración central del repositorio
│   ├── manage_video_toolkit.ps1            # interfaz para Windows PowerShell
│   ├── manage_video_toolkit.sh              # interfaz para Ubuntu/Bash
│   └── lib/
│       ├── VideoToolkit.Infrastructure.psm1 # infraestructura compartida de PowerShell
│       └── VideoToolkit.Infrastructure.sh   # infraestructura compartida de Bash
├── src/
│   ├── shared/video_toolkit/               # paquete y utilidades Python comunes
│   ├── video-generate-new-subtitles-from-audio/
│   ├── video-generate-traslated-subtitles-from-existing-subtitles/
│   └── video-generate-whisper-transcription/
├── tests/                                  # pruebas compartidas y arquitectónicas
├── pyproject.toml
├── requirements.txt
└── requirements-whisperx.txt
```

Las carpetas `inputs/`, `outputs/` y `.venv/` son áreas locales intencionales. `.tmp/` contiene solamente archivos efímeros generados durante build, pruebas y procesamiento; `.cache/` conserva descargas y resultados técnicos regenerables entre ejecuciones. Git conserva únicamente los archivos `.gitkeep` de ambas carpetas.

`outputs/` contiene entregables funcionales vinculados a un video. Una futura carpeta raíz `dist/` queda reservada para exportaciones globales de negocio solicitadas explícitamente por el usuario; la instalación, el build de Python y los workflows actuales no la crean ni la limpian. Los wheels técnicos opcionales se guardan en `.cache/packages/python/`. `.configs/` no se crea porque los pesos descargados son caché, no configuración; si más adelante se incorporan perfiles TOML, YAML o JSON persistentes, entonces podrán vivir allí.

### Administración centralizada

Los antiguos scripts separados de instalación, build, pruebas y limpieza fueron fusionados en una interfaz por sistema operativo. Ambos administradores ofrecen las mismas operaciones y evitan dejar `build/` o `video_toolkit_workflows.egg-info/` en la raíz:

| Operación | PowerShell | Bash |
|---|---|---|
| Preparar `.venv/` | `manage_video_toolkit.ps1 setup-python-environment` | `manage_video_toolkit.sh setup-python-environment` |
| Construir el wheel | `manage_video_toolkit.ps1 build-python-package` | `manage_video_toolkit.sh build-python-package` |
| Ejecutar todas las pruebas | `manage_video_toolkit.ps1 run-test-suite` | `manage_video_toolkit.sh run-test-suite` |
| Limpiar temporales efímeros | `manage_video_toolkit.ps1 clean-temporary-files` | `manage_video_toolkit.sh clean-temporary-files` |
| Limpiar cachés regenerables | `manage_video_toolkit.ps1 clean-cache-files` | `manage_video_toolkit.sh clean-cache-files` |
| Verificar la estructura | `manage_video_toolkit.ps1 verify-repository` | `manage_video_toolkit.sh verify-repository` |
| Mostrar ayuda | `manage_video_toolkit.ps1 help` | `manage_video_toolkit.sh help` |

En PowerShell antepone `powershell -ExecutionPolicy Bypass -File .\scripts\`; en Ubuntu antepone `bash ./scripts/`. La limpieza temporal y la limpieza de caché son operaciones deliberadamente separadas. Los archivos `VideoToolkit.Infrastructure.psm1` y `VideoToolkit.Infrastructure.sh` no son comandos de usuario: concentran la resolución segura de `.tmp/` y `.cache/`, sus variables de entorno y las funciones reutilizables de cada sistema. Los tres launchers PowerShell importan el primero; `manage_video_toolkit.sh` carga el segundo mediante `source`.

#### Diferencia entre `.ps1` y `.psm1`

Los archivos `.ps1` son puntos de entrada ejecutables. `manage_video_toolkit.ps1` y los tres launchers ubicados bajo `src/` se ejecutan desde una terminal PowerShell con `-File`. No se recomienda iniciarlos mediante doble clic porque la consola puede cerrarse al terminar y ocultar mensajes o errores.

Los archivos `.psm1` son módulos de funciones compartidas. `scripts/lib/VideoToolkit.Infrastructure.psm1` no debe ejecutarse directamente, asociarse a `powershell.exe` para doble clic ni pasarse a `powershell -File`; Windows PowerShell 5.1 solo acepta `.ps1` con `-File`. Los scripts ejecutables cargan el módulo internamente mediante:

```powershell
Import-Module .\scripts\lib\VideoToolkit.Infrastructure.psm1
```

Para comprobar los comandos disponibles sin ejecutar un workflow de video:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\manage_video_toolkit.ps1 `
  help
```

Para abrir o editar un `.psm1`, usa VS Code, PowerShell ISE o un editor de texto. La versión Bash sigue el mismo principio: `manage_video_toolkit.sh` es la interfaz ejecutable y `VideoToolkit.Infrastructure.sh` es una biblioteca cargada con `source`.

## Requisitos

### Sistema

- Windows PowerShell 5.1 o PowerShell 7;
- Python 3.12;
- `ffmpeg` y `ffprobe` disponibles en `PATH`;
- `mkvmerge` de MKVToolNix para los workflows que entregan MKV;
- espacio suficiente para WAV temporales y copias remuxeadas del video;
- GPU NVIDIA/CUDA opcional, pero recomendada para WhisperX `large-v3`.

No se necesitan API keys. WhisperX y OpenAI Whisper se ejecutan localmente.

### Comprobar herramientas

Ejecuta desde la raíz del repositorio:

```powershell
py -3.12 --version
ffmpeg -version
ffprobe -version
mkvmerge --version
```

Si uno de estos comandos no existe, instala la herramienta correspondiente y vuelve a abrir la terminal para actualizar `PATH`.

### Crear o reparar el entorno Python

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\scripts\manage_video_toolkit.ps1 `
  setup-python-environment
```

En Ubuntu:

```bash
bash ./scripts/manage_video_toolkit.sh setup-python-environment
```

El inicializador:

1. localiza Python 3.12;
2. crea o valida `.venv/`;
3. instala las dependencias requeridas de `requirements.txt`;
4. intenta instalar las dependencias preferidas de WhisperX;
5. mantiene OpenAI Whisper como fallback cuando WhisperX no está disponible.

No instales WhisperX globalmente. Los launchers priorizan siempre `.venv/Scripts`.

### Reconstruir `.venv` en otro computador

Hay dos rutas soportadas.

#### Ruta recomendada: bootstrap del proyecto

Esta ruta conserva la lógica del repositorio para Python 3.12, requirements, WhisperX opcional y PyTorch CUDA:

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\scripts\manage_video_toolkit.ps1 `
  setup-python-environment
```

Para una GPU NVIDIA/CUDA:

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\scripts\manage_video_toolkit.ps1 `
  setup-python-environment `
  -EnsureCudaTorch
```

Los launchers de audio y texto activan `-EnsureCudaTorch` automáticamente cuando se ejecutan con `-Device cuda`. Si quieres una instalación CPU, usa `-Device cpu` y no necesitas instalar el índice CUDA.

`.venv/` es específica del sistema operativo: una instalación creada en Windows no debe reutilizarse desde Ubuntu, ni al contrario. En otro computador o al cambiar de sistema, recrea `.venv/` con el script correspondiente.

El script utiliza:

- `requirements.txt` para la dependencia base `openai-whisper`;
- `requirements-whisperx.txt` para el backend opcional WhisperX;
- el índice PyTorch CUDA configurado en el propio script cuando se solicita `-EnsureCudaTorch`;
- marcadores SHA-256 dentro de `.cache/install-state/` para no reinstalar mientras las requirements no cambien.

#### Ruta administrada PEP 621: `pyproject.toml`

El archivo [pyproject.toml](C:/Development/Proyectos/Video/pyproject.toml:1) declara Python 3.12, las dependencias y los cuatro namespaces instalables (`video_toolkit` más los tres paquetes de workflow). No ejecutes `pip install .`, `pip wheel .` ni `python -m build` directamente desde la raíz: usa los scripts administrados para que `build` y `*.egg-info` permanezcan bajo `.tmp/` y el wheel opcional quede bajo `.cache/packages/python/`.

En Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\manage_video_toolkit.ps1 setup-python-environment
powershell -ExecutionPolicy Bypass -File .\scripts\manage_video_toolkit.ps1 build-python-package
```

En Ubuntu:

```bash
bash ./scripts/manage_video_toolkit.sh setup-python-environment
bash ./scripts/manage_video_toolkit.sh build-python-package
```

El wheel instalable queda en `.cache/packages/python/`. Es un artefacto opcional y regenerable: no se instala automáticamente dentro de `.venv/` y ninguno de los tres workflows lo necesita para ejecutarse. Los launchers trabajan directamente con `src/` y siguen siendo la interfaz recomendada porque configuran las rutas compartidas, los workspaces y las herramientas externas. El comando `setup-python-environment` instala el backend base y trata WhisperX como dependencia preferida opcional; `-EnsureCudaTorch` en PowerShell o `--ensure-cuda-torch` en Bash fuerza la validación CUDA.

Después de una instalación PEP 621, comprueba el entorno:

```powershell
.\.venv\Scripts\python.exe -m pip check
powershell -ExecutionPolicy Bypass -File `
  .\scripts\manage_video_toolkit.ps1 `
  run-test-suite
```

`pyproject.toml` centraliza la declaración de dependencias, pero no puede instalar herramientas del sistema como FFmpeg, FFprobe o MKVToolNix, ni puede elegir una build CUDA compatible con cada driver NVIDIA. Esas piezas deben instalarse en el computador destino y verificarse con los comandos de la sección anterior.

Las versiones declaradas usan rangos compatibles, no un lock binario específico de Windows/CUDA. Para congelar una instalación concreta después de validar una máquina:

```powershell
.\.venv\Scripts\python.exe -m pip freeze `
  | Set-Content -Encoding UTF8 .\requirements-lock-py312.txt
```

Ese lock debe tratarse como específico de plataforma, arquitectura, versión de Python y variante CUDA. No reemplaza a `requirements.txt`, `requirements-whisperx.txt` ni `pyproject.toml`, que siguen siendo las declaraciones portables del proyecto.

### Ejecutar las pruebas

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\scripts\manage_video_toolkit.ps1 `
  run-test-suite
```

En Ubuntu:

```bash
bash ./scripts/manage_video_toolkit.sh run-test-suite
```

La suite descubre las pruebas permanentes ubicadas directamente en `tests/` y las pruebas propias de los tres subproyectos. `.tmp/tests/` se usa exclusivamente para workspaces temporales de ejecución y se limpia después de una suite exitosa.

### Limpiar temporales

La limpieza temporal elimina workspaces de build, metadatos, runtime, pruebas y logs bajo `.tmp/`, pero conserva `.cache/`, `.venv/`, `inputs/` y `outputs/`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\manage_video_toolkit.ps1 clean-temporary-files
```

```bash
bash ./scripts/manage_video_toolkit.sh clean-temporary-files
```

Para vaciar explícitamente cachés de pip y Python, modelos descargados, estado de instalación y wheels opcionales:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\manage_video_toolkit.ps1 clean-cache-files
```

```bash
bash ./scripts/manage_video_toolkit.sh clean-cache-files
```

Eliminar `.cache/` no rompe el código fuente ni `.venv/`, pero la siguiente ejecución puede volver a descargar modelos o dependencias y recalcular el estado de instalación. Ninguna limpieza elimina `.venv/`, `inputs/`, `outputs/`, una futura `dist/` de negocio ni una futura `.configs/`.

## Convenciones de entrada

La carpeta canónica es `inputs/`.

```text
inputs/
├── pelicula.mkv
├── entrevista.mp4
└── curso/
    ├── modulo-01.mp4
    └── modulo-02.mp4
```

Reglas comunes:

- las rutas relativas se resuelven desde el repositorio y desde `inputs/` según el launcher;
- una ruta absoluta también es válida;
- si un workflow de un solo archivo encuentra varios candidatos y no se especifica `-InputMkv` o `-InputVideo`, se detiene en lugar de elegir arbitrariamente;
- el modo carpeta de la transcripción Whisper es no recursivo;
- dos archivos de un mismo lote no pueden tener el mismo nombre sin extensión, porque compartirían el mismo destino determinista;
- el archivo debe contener video y audio para los workflows de transcripción;
- el workflow de traducción acepta exclusivamente un MKV con subtítulos incrustados de texto.

## Contrato de salida y limpieza segura

Cada archivo usa su nombre completo sin extensión como `<stem>`:

```text
inputs/Mi video.final.mp4
└── outputs/Mi video.final/
```

No se agregan hashes, IDs de workspace ni sufijos aleatorios. Una ejecución nueva:

1. calcula `outputs/<stem>/`;
2. verifica que sea hijo directo de `outputs/`;
3. rechaza destinos que sean reparse points o contengan reparse points;
4. elimina únicamente el contenido previo de ese destino exacto;
5. crea `debug/<workflow>/run_manifest.json`;
6. genera los nuevos artefactos.

Consecuencias importantes:

- volver a ejecutar un mismo archivo reemplaza su workspace anterior;
- `-DryRun` en los dos workflows de Whisper inspecciona y muestra el comando, pero no limpia ni crea el workspace;
- el workflow de traducción no tiene `-DryRun`;
- `-Resume` es la única modalidad que conserva el checkpoint y los mapas del workflow de traducción;
- `_legacy` es un nombre reservado y nunca puede ser utilizado como destino normal;
- las antiguas carpetas raíz `subtitle_work/`, `translations/` y `tools/` no forman parte del runtime.

Estructura general:

```text
outputs/<stem>/
├── <entregables públicos>
├── sidecars/                         # solo exportaciones solicitadas
└── debug/
    └── <workflow>/
        ├── run_manifest.json
        ├── audio/
        ├── whisper/
        ├── postprocess/
        ├── subtitles/
        ├── translations/
        ├── checkpoints/
        └── reports/
```

No todas las subcarpetas aparecen en todos los workflows.

---

## Workflow 1: traducir subtítulos existentes

Nombre exacto:

```text
video-generate-traslated-subtitles-from-existing-subtitles
```

### Cuándo usarlo

Úsalo cuando el archivo sea MKV y ya contenga al menos una pista textual de subtítulos en un idioma compatible. Este workflow traduce subtítulos; no transcribe voces.

No lo uses cuando:

- el video no tenga subtítulos incrustados;
- la única pista sea gráfica, por ejemplo PGS;
- necesites solamente un documento Markdown;
- el archivo de entrada no sea MKV.

En esos casos usa primero `video-generate-new-subtitles-from-audio` o utiliza `video-generate-whisper-transcription`, según el resultado deseado.

### Invocarlo desde Codex

```text
$video-generate-traslated-subtitles-from-existing-subtitles procesa inputs/pelicula.mkv y traduce la pista principal a español LatAm
```

También puedes indicar la pista exacta:

```text
$video-generate-traslated-subtitles-from-existing-subtitles procesa inputs/pelicula.mkv usando el stream de subtítulos 4
```

La skill coordina inspección del contenedor, segmentación semántica, traducción de diálogo, reconstrucción segura de canciones, revisión lingüística y validación técnica.

### Ejecución directa mínima

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-generate-traslated-subtitles-from-existing-subtitles\traducir_subs_mkv.ps1 `
  -InputMkv ".\inputs\pelicula.mkv"
```

### Selección de la pista de subtítulos

Sin `-SourceSubtitleStreamIndex`, el launcher:

1. usa la pista predeterminada cuando es textual y su idioma está soportado;
2. si no hay una predeterminada utilizable, inspecciona todas las candidatas;
3. prefiere pistas completas frente a `Forced`;
4. prefiere no-CC/no-SDH salvo solicitud expresa;
5. considera cobertura, duración, idioma y metadata;
6. informa el índice `ffprobe` y el track ID de `mkvmerge` seleccionados.

Para fijar una pista:

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-generate-traslated-subtitles-from-existing-subtitles\traducir_subs_mkv.ps1 `
  -InputMkv ".\inputs\pelicula.mkv" `
  -SourceSubtitleStreamIndex 4
```

El índice corresponde al campo `stream.index` de `ffprobe`, no necesariamente a la posición visual mostrada por un reproductor.

### Idiomas de origen soportados

- inglés;
- chino mandarín;
- hindi;
- portugués;
- francés;
- ruso;
- alemán;
- japonés;
- chino Wu/Shanghainés;
- coreano;
- italiano.

Puedes usar `-SourceLanguageOverride <código>` para corregir metadata incorrecta, pero el override no convierte un idioma no soportado en soportado.

### Formatos de subtítulos

| Formato incrustado | Comportamiento |
|---|---|
| ASS/SSA textual | Entra directamente al pipeline estructural |
| SRT/SubRip | Se convierte a ASS simple antes de aplicar traducciones |
| VTT/WebVTT | Se convierte a ASS simple antes del procesamiento |
| PGS u otro formato gráfico | No soportado; el workflow se detiene |

ASS conserva estilos, posiciones y signos cuando es seguro. Para karaoke, dibujos vectoriales o efectos complejos se genera una variante simplificada TV-safe. Nunca se traducen como texto visible comandos `\p`, rutas `m/l/b`, tags `\pos`, `\move`, `\t` ni fragmentos numéricos.

### Fases del workflow

1. Inspecciona el MKV, sus pistas, idiomas, codecs, attachments y defaults.
2. Selecciona y extrae la pista fuente.
3. Convierte SRT/VTT a ASS cuando sea necesario.
4. Separa texto visible de tags y efectos.
5. Agrupa eventos adyacentes en oraciones, signos o unidades líricas completas.
6. Reconstruye canciones por línea y omite intervalos inseguros.
7. Traduce a español latinoamericano con contexto semántico.
8. Revisa terminología, naturalidad, puntuación y continuidad.
9. Aplica mapas terminológicos.
10. Genera ASS traducido y SRT TV-safe según `-EmbeddedSubtitleFormat`.
11. Remuxea con `mkvmerge` conservando las pistas originales.
12. Extrae y valida la pista española final.

### Checkpoint y mapas de traducción

El launcher extrae primero el subtítulo fuente. Si no encuentra mapas, crea:

```text
outputs/<stem>/debug/video-generate-traslated-subtitles-from-existing-subtitles/
├── checkpoints/
│   └── translation_checkpoint.json
├── subtitles/
│   └── source/
│       └── <stem>.source.ass
└── translations/
    └── <source_lang>/
        └── README.txt
```

Después termina deliberadamente con:

```text
[CHECKPOINT:AWAITING_TRANSLATION_MAPS]
```

Esto no representa un fallo de extracción. El checkpoint registra:

- input absoluto;
- subtítulo fuente exacto;
- idioma y codec;
- índice `ffprobe`;
- track ID de `mkvmerge`;
- directorio esperado de mapas;
- parámetros efectivos;
- comando PowerShell completo de reanudación.

Los mapas se resuelven con esta prioridad:

1. `translations_all.json` cuando existe;
2. en su ausencia, todos los `translations_*.json` ordenados por nombre;
3. `-TranslationJson` cuando el usuario proporciona rutas explícitas.

Ejemplo simplificado de mapa:

```json
{
  "123": "No podemos retirarnos ahora.",
  "124": "La batalla apenas ha comenzado.",
  "SongStyle|0:12:34.50|0:12:39.20": "Seguiremos caminando bajo el mismo cielo."
}
```

Las claves numéricas son números de línea reales del ASS extraído. Las claves con `|` representan grupos de canción con `estilo|inicio|fin`. No inventes claves ni reutilices mapas de otro video.

Guarda el mapa preferido en:

```text
outputs/<stem>/debug/video-generate-traslated-subtitles-from-existing-subtitles/
└── translations/<source_lang>/translations_all.json
```

Luego ejecuta **exactamente** `resume.command` desde `translation_checkpoint.json`. No lances otra ejecución limpia, porque borraría el checkpoint y los mapas.

### Mapas terminológicos

`-TermMapJson` acepta uno o más JSON con reemplazos fuente-destino:

```json
{
  "Kingdom of Wei": "Reino de Wei",
  "Lord Nobunaga": "señor Nobunaga",
  "Ryuumon": "Ryūmon"
}
```

Ejemplo:

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-generate-traslated-subtitles-from-existing-subtitles\traducir_subs_mkv.ps1 `
  -InputMkv ".\inputs\pelicula.mkv" `
  -TermMapJson ".\terminologia\pelicula.json"
```

Los reemplazos se aplican de las cadenas más largas a las más cortas después de cargar los términos internos. Usa mapas específicos del video o la serie y revísalos antes del remux.

### Elegir ASS, SRT o ambos

```powershell
# Máxima fidelidad visual
-EmbeddedSubtitleFormat ass

# Máxima compatibilidad de reproducción
-EmbeddedSubtitleFormat srt

# Recomendado: fidelidad más fallback TV-safe
-EmbeddedSubtitleFormat both
```

Con `both`:

1. `Español LatAm` ASS queda como primera pista de subtítulos y única predeterminada;
2. `Español LatAm TV-safe` SRT queda inmediatamente después y no es predeterminada;
3. todas las pistas originales se conservan, pero se marcan como no predeterminadas.

### Parámetros del launcher de traducción

| Parámetro | Uso |
|---|---|
| `-InputMkv` | Ruta del MKV fuente. Si se omite, `inputs/` debe contener exactamente un MKV |
| `-SourceSubtitleStreamIndex` | Índice `ffprobe` de la pista textual que se debe traducir |
| `-SourceMkvTrackId` | Track ID de `mkvmerge`; normalmente lo calcula el launcher o lo recupera el checkpoint |
| `-SourceLanguageOverride` | Corrige el código de idioma cuando la metadata es errónea |
| `-EmbeddedSubtitleFormat` | `ass`, `srt` o `both`; valor predeterminado `both` |
| `-TranslationJson` | Una o más rutas explícitas a mapas de traducción |
| `-TermMapJson` | Uno o más glosarios JSON |
| `-Resume` | Conserva y valida el workspace preparado; debe usarse con el contexto del checkpoint |
| `-SkipSpanishNormalization` | Omite la normalización lingüística/técnica final; solo para diagnóstico |
| `-EnglishAss` | Override avanzado de la ruta ASS fuente interna |
| `-SpanishAss` | Override avanzado del ASS español interno |
| `-TvSafeSrt` | Override avanzado del SRT TV-safe interno |
| `-NormalizationReport` | Override avanzado del reporte de normalización |
| `-OutputMkv` | Override del nombre final, siempre dentro de `outputs/<stem>/` |

Los overrides de artefactos están restringidos al workspace determinista; no pueden escribir fuera de sus subdirectorios permitidos.

### Salida del workflow de traducción

```text
outputs/<stem>/
├── <stem>.spa.mkv
└── debug/
    └── video-generate-traslated-subtitles-from-existing-subtitles/
        ├── run_manifest.json
        ├── checkpoints/
        │   └── translation_checkpoint.json
        ├── subtitles/
        │   ├── source/<stem>.source.ass
        │   └── generated/
        │       ├── <stem>.spa.ass
        │       └── <stem>.spa.srt
        ├── translations/<source_lang>/
        └── reports/
            ├── spanish_normalization_report.json
            └── remux_validation_report.json
```

El único archivo público en la raíz es el MKV final. Los ASS/SRT son internos para impedir que un reproductor cargue una copia externa como pista `[Local]`.

---

## Workflow 2: crear subtítulos nuevos desde el audio

Nombre exacto:

```text
video-generate-new-subtitles-from-audio
```

### Cuándo usarlo

Úsalo cuando el video tenga voces pero no una pista de subtítulos textual utilizable y quieras terminar con un MKV subtitulado en el idioma hablado.

Este workflow:

- transcribe, no traduce;
- procesa un video por ejecución;
- acepta cualquier contenedor que FFmpeg pueda decodificar;
- produce siempre un MKV cuando el remux está habilitado;
- puede preparar el MKV para el workflow posterior de traducción.

Formatos comunes aceptados: MKV, MP4, MOV, M4V, WebM, AVI, WMV, FLV, TS/M2TS, MPEG/MPG, 3GP/3G2 y OGV.

### Invocarlo desde Codex

```text
$video-generate-new-subtitles-from-audio crea subtítulos desde el audio de inputs/entrevista.mp4
```

Para elegir una pista de audio:

```text
$video-generate-new-subtitles-from-audio procesa inputs/pelicula.mkv usando el stream de audio 2 y conserva el idioma japonés
```

### Ejecución directa mínima

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-generate-new-subtitles-from-audio\transcribe_video_audio.ps1 `
  -InputVideo ".\inputs\entrevista.mp4"
```

### Selección de audio e idioma

Sin `-AudioStreamIndex`, el launcher selecciona:

1. la primera pista marcada como predeterminada;
2. si ninguna es predeterminada, la primera pista de audio;
3. si varias son predeterminadas, la primera en orden de contenedor y muestra una advertencia.

Para elegir una pista concreta:

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-generate-new-subtitles-from-audio\transcribe_video_audio.ps1 `
  -InputVideo ".\inputs\pelicula.mkv" `
  -AudioStreamIndex 2 `
  -Language ja
```

`-Language` usa códigos Whisper como `es`, `en`, `ja`, `fr`, `de`, `pt` o `zh`. Si se omite, el launcher intenta convertir la metadata de la pista seleccionada (`eng`, `jpn`, `fre`, etc.) a un código Whisper. Si la metadata es desconocida, el backend puede autodetectar.

### Backend de transcripción

`-Backend auto` aplica esta política:

1. usa WhisperX desde `.venv/Scripts` si está disponible;
2. si WhisperX no está disponible, usa OpenAI Whisper local;
3. si ninguno existe, termina con un error claro.

Defaults:

| Backend | Modelo | Dispositivo | Precisión |
|---|---|---|---|
| WhisperX | `large-v3` | `cuda` | `float16`, batch 8 |
| OpenAI Whisper | `turbo` | `cuda` | fp16 |

No se usa diarización ni `--task translate`.

Ejemplo para CPU:

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-generate-new-subtitles-from-audio\transcribe_video_audio.ps1 `
  -InputVideo ".\inputs\entrevista.mp4" `
  -Device cpu `
  -ComputeType int8 `
  -Fp16 $false `
  -BatchSize 4
```

### Inspeccionar sin procesar

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-generate-new-subtitles-from-audio\transcribe_video_audio.ps1 `
  -InputVideo ".\inputs\entrevista.mp4" `
  -DryRun
```

`-DryRun` valida herramientas, resuelve el video, selecciona el audio, inicializa el entorno, resuelve el backend y muestra el comando. No extrae audio, no transcribe, no remuxea y no limpia `outputs/<stem>/`.

### Postproceso de subtítulos

El audio se extrae como WAV mono a 16 kHz. Después del backend:

- se rechazan transcripciones vacías;
- se eliminan cues vacíos o inválidos;
- se limitan los subtítulos a dos líneas visibles por defecto;
- los cues largos se dividen secuencialmente dentro de su intervalo;
- WhisperX aporta timestamps por palabra cuando están disponibles;
- sin timestamps por palabra, el tiempo se distribuye proporcionalmente;
- el SRT limpio queda como input interno del remux.

El SRT interno no se publica junto al MKV, porque su timeline previo al remux puede diferir del timeline final normalizado.

### Estrategia de remux y sincronización

Para MKV/WebM se usa `mkvmerge`, conservando pistas y attachments.

Para MP4, MOV y otros contenedores no Matroska se usa una sola invocación FFmpeg que recibe simultáneamente:

- video original;
- audio original;
- demás streams copiables;
- SRT transcrito.

Esto aplica la misma transformación dinámica de timestamps a medios y subtítulos, incluyendo edit lists o preroll negativo. No se usa un delay fijo, `-ss 0` ni un intermedio de video sin subtítulos.

La validación comprueba que todos los cues reciban un desplazamiento uniforme con una dispersión máxima de 5 ms.

### Exportar un ASS opcional

Por defecto solo se publica el MKV:

```text
outputs/<stem>/<stem>.transcribed.mkv
```

Para obtener también un ASS:

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-generate-new-subtitles-from-audio\transcribe_video_audio.ps1 `
  -InputVideo ".\inputs\entrevista.mp4" `
  --export-ass-file-subtitles
```

También se acepta el switch PowerShell:

```powershell
-ExportAssFileSubtitles
```

El ASS se crea extrayendo la pista ya normalizada del MKV final, no convirtiendo el SRT previo al remux. Se publica en:

```text
outputs/<stem>/sidecars/<stem>.transcribed.ass
```

`-SkipRemux` y `--export-ass-file-subtitles` son incompatibles.

### Parámetros del launcher desde audio

| Parámetro | Uso |
|---|---|
| `-InputVideo` | Video fuente. `-InputMkv` funciona como alias |
| `-AudioStreamIndex` | Índice `ffprobe` de audio; `-1` selecciona default y luego primero |
| `-Language` | Código Whisper explícito |
| `-Backend` | `auto`, `whisperx` o `whisper` |
| `-WhisperXModel` | Modelo WhisperX; default `large-v3` |
| `-WhisperModel` | Modelo OpenAI Whisper; default `turbo` |
| `-Device` | Normalmente `cuda` o `cpu` |
| `-ComputeType` | Precisión WhisperX, por ejemplo `float16` o `int8` |
| `-BatchSize` | Tamaño de batch WhisperX; default 8 |
| `-MaxSubtitleLines` | Máximo de líneas visibles por cue; default 2 |
| `-MaxSubtitleLineChars` | Objetivo de caracteres por línea; default 52 |
| `-Fp16` | Controla fp16 en OpenAI Whisper |
| `-SkipRemux` | Conserva el SRT limpio interno sin producir el MKV; solo diagnóstico |
| `-DryRun` | Muestra el plan sin escribir el workspace |
| `-ExportAssFileSubtitles` | Publica un ASS sincronizado bajo `sidecars/` |

### Salida del workflow desde audio

```text
outputs/<stem>/
├── <stem>.transcribed.mkv
├── sidecars/
│   └── <stem>.transcribed.ass              # solo si se solicita
└── debug/
    └── video-generate-new-subtitles-from-audio/
        ├── run_manifest.json
        ├── audio/<stem>.audio.wav
        ├── whisper/                        # outputs nativos del backend
        ├── postprocess/<stem>.transcribed.srt
        └── reports/
            ├── transcription_report.json
            └── remux_validation.json
```

El MKV añade una pista SRT predeterminada con idioma detectado/solicitado y título `Transcripción <idioma>`.

---

## Workflow 3: generar transcripción Whisper para texto y RAG

Nombre exacto:

```text
video-generate-whisper-transcription
```

### Cuándo usarlo

Úsalo para obtener texto del contenido hablado sin crear ni modificar un MKV. Es apropiado para:

- bases de conocimiento RAG;
- búsqueda semántica;
- documentación de cursos, reuniones o entrevistas;
- revisión editorial;
- transcripciones SRT públicas;
- procesamiento por lotes de una carpeta.

Este workflow no traduce, no remuxea y no incrusta subtítulos en el video.

### Invocarlo desde Codex

```text
$video-generate-whisper-transcription transcribe inputs/curso/modulo-01.mp4 para RAG
```

Modo carpeta:

```text
$video-generate-whisper-transcription transcribe todos los videos de inputs/curso/ sin recorrer subcarpetas
```

La skill detecta o propone el idioma, muestra el código/nombre/confianza y solicita confirmación antes de la transcripción definitiva. La pausa se omite únicamente cuando se indica expresamente que el idioma ya está confirmado o se solicita ejecución no interactiva.

### Ejecución directa recomendada

Después de confirmar el idioma:

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-generate-whisper-transcription\transcribe_video_text.ps1 `
  -InputPath ".\inputs\curso\modulo-01.mp4" `
  -Language es
```

Aunque el launcher permite omitir `-Language`, la ejecución definitiva controlada debe pasarlo explícitamente después de confirmar el idioma.

### Detectar el idioma antes de transcribir

```powershell
.\.venv\Scripts\python.exe `
  .\.agents\skills\video-generate-whisper-transcription\scripts\detect_language.py `
  --input ".\inputs\curso\modulo-01.mp4" `
  --model large-v3 `
  --device cuda `
  --compute-type float16 `
  --json
```

El detector toma muestras tempranas, medias y tardías. Una confianza inferior a `0.60` o desacuerdo entre muestras se considera incierto, pero la decisión final siempre corresponde al usuario. No se corrige el idioma basándose únicamente en el nombre del archivo o la metadata.

### Procesar una carpeta

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-generate-whisper-transcription\transcribe_video_text.ps1 `
  -InputPath ".\inputs\curso" `
  -Language es
```

El modo carpeta:

- procesa archivos válidos no recursivamente y en orden por nombre;
- valida que cada archivo tenga video y audio;
- rechaza stems duplicados antes de comenzar;
- crea un workspace independiente por video;
- continúa después de fallos individuales;
- devuelve código de salida distinto de cero si al menos un archivo falla;
- muestra al final los videos procesados y fallidos.

### Calidad WhisperX

Modo equilibrado, predeterminado:

```powershell
-WhisperXQuality balanced
```

Usa beam 5 y patience 1.

Modo de máxima calidad:

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-generate-whisper-transcription\transcribe_video_text.ps1 `
  -InputPath ".\inputs\curso\modulo-01.mp4" `
  -Language es `
  -WhisperXQuality maximum `
  -WhisperXInitialPrompt "Curso de arquitectura de software" `
  -WhisperXHotwords "Kubernetes, PostgreSQL, Dijkstra"
```

`maximum` usa beam 10 y patience 2. Los prompts y hotwords deben ser breves, verificables y específicos del dominio; no los derives ciegamente de una transcripción ruidosa.

Para comparaciones A/B se pueden ajustar `-WhisperXBeamSize`, `-WhisperXPatience`, `-WhisperXLengthPenalty`, VAD y chunk size. Conserva los defaults si no tienes una medición concreta.

### Modo limpio frente a modo verbatim

Modo normal:

- limpia ruido no verbal;
- elimina saludos vacíos, boilerplate, clutter promocional y fillers excesivos;
- repara duplicados y artefactos de encoding;
- conserva conceptos, procesos, ejemplos, decisiones y terminología;
- mejora puntuación de forma conservadora;
- no resume el contenido.

Modo literal:

```powershell
-Verbatim
```

`-Verbatim` conserva palabras reconocidas, repeticiones, fillers y etiquetas de ruido. Solo repara encoding y espacios. El Markdown y el reporte registran `postprocess_mode: verbatim`.

### Inspeccionar sin transcribir

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-generate-whisper-transcription\transcribe_video_text.ps1 `
  -InputPath ".\inputs\curso\modulo-01.mp4" `
  -Language es `
  -DryRun
```

En modo carpeta muestra un plan por video. No extrae audio, no ejecuta Whisper y no limpia los destinos.

### Estructura del Markdown RAG

Cada Markdown público contiene:

- frontmatter YAML con título, video fuente, backend, idioma, stream de audio y fecha;
- un H1 con el nombre del video;
- un H2 por párrafo con su rango temporal;
- párrafos legibles que conservan el significado hablado;
- UTF-8 limpio y correcciones conservadoras.

Ejemplo conceptual:

```markdown
---
title: "Módulo 1"
source_video: "modulo-01.mp4"
backend: "whisperx"
language: "es"
audio_stream_index: 1
---

# Módulo 1

## 00:00:04 - 00:01:12

En este módulo se explica cómo separar las responsabilidades del dominio...
```

`-ParagraphMaxChars` limita el tamaño aproximado de los párrafos. `-SectionSeconds` se mantiene como parámetro de compatibilidad del postproceso, pero la estructura pública actual usa timestamps derivados de cada párrafo.

### Parámetros del launcher de texto

| Parámetro | Uso |
|---|---|
| `-InputPath` | Archivo o carpeta no recursiva |
| `-AudioStreamIndex` | Stream de audio; `-1` selecciona default y luego primero |
| `-Language` | Código Whisper confirmado |
| `-Backend` | `auto`, `whisperx` o `whisper` |
| `-WhisperXModel` | Modelo WhisperX; default `large-v3` |
| `-WhisperModel` | Modelo OpenAI Whisper; default `turbo` |
| `-Device` | `cuda` o `cpu` |
| `-ComputeType` | `float16`, `int8` u otra precisión soportada |
| `-BatchSize` | Batch WhisperX; default 8 |
| `-WhisperXQuality` | `balanced` o `maximum` |
| `-WhisperXBeamSize` | Override explícito del beam; 0 conserva el preset |
| `-WhisperXPatience` | Override explícito de patience; 0 conserva el preset |
| `-WhisperXLengthPenalty` | Penalización de longitud; default 1.0 |
| `-WhisperXInitialPrompt` | Contexto breve verificado |
| `-WhisperXHotwords` | Términos raros o técnicos esperados |
| `-WhisperXVadMethod` | `pyannote` o `silero`; default `pyannote` |
| `-WhisperXVadOnset` | Umbral VAD de inicio; default 0.5 |
| `-WhisperXVadOffset` | Umbral VAD de fin; default 0.363 |
| `-WhisperXChunkSize` | Tamaño de chunk; default 30 segundos |
| `-SectionSeconds` | Parámetro compatible de agrupación; default 180 |
| `-ParagraphMaxChars` | Tamaño objetivo de párrafo; default 900 |
| `-Fp16` | Controla fp16 en OpenAI Whisper |
| `-Verbatim` | Desactiva la limpieza semántica y conserva el habla reconocida |
| `-DryRun` | Inspecciona comandos sin escribir outputs |

### Salida del workflow de texto

```text
outputs/<stem>/
├── <stem>.srt
├── <stem>.md
└── debug/
    └── video-generate-whisper-transcription/
        ├── run_manifest.json
        ├── audio/<stem>.wav
        ├── whisper/
        │   ├── raw/
        │   │   ├── <stem>.json
        │   │   ├── <stem>.srt
        │   │   ├── <stem>.vtt
        │   │   ├── <stem>.txt
        │   │   └── <stem>.tsv
        │   └── postprocess/
        │       ├── <stem>.vtt
        │       └── <stem>.txt
        └── reports/
            └── text_transcription_report.json
```

Los únicos archivos públicos son SRT y Markdown. JSON, VTT, TXT y TSV nativos permanecen bajo `debug/`.

---

## Encadenar creación y traducción de subtítulos

Cuando un MP4/MOV/MKV no tiene subtítulos y el objetivo final es un MKV en español LatAm:

### Paso 1: crear la pista fuente desde el audio

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-generate-new-subtitles-from-audio\transcribe_video_audio.ps1 `
  -InputVideo ".\inputs\pelicula.mp4" `
  -Language ja
```

Resultado:

```text
outputs/pelicula/pelicula.transcribed.mkv
```

### Paso 2: traducir el MKV generado

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\src\video-generate-traslated-subtitles-from-existing-subtitles\traducir_subs_mkv.ps1 `
  -InputMkv ".\outputs\pelicula\pelicula.transcribed.mkv"
```

El segundo archivo tiene stem `pelicula.transcribed`, por lo que su workspace será:

```text
outputs/pelicula.transcribed/
```

La pista SRT creada en el primer paso es textual y puede ser extraída y convertida a ASS simple por el workflow de traducción.

## Solución de problemas

### `ffmpeg`, `ffprobe` o `mkvmerge` no está en PATH

Comprueba los comandos desde la misma terminal. Si instalaste una herramienta recientemente, cierra y abre PowerShell.

### Hay varios archivos en `inputs/`

Pasa una ruta exacta con `-InputMkv`, `-InputVideo` o `-InputPath`. Los workflows no eligen arbitrariamente entre varios candidatos.

### El MKV no tiene subtítulos

Usa `video-generate-new-subtitles-from-audio`. El workflow de traducción no transcribe audio.

### La pista es PGS

PGS es un formato gráfico y no puede entrar al pipeline textual. Crea subtítulos desde el audio o realiza OCR fuera de este toolkit.

### Idioma de subtítulos no soportado

El workflow de traducción se detiene antes de generar resultados engañosos. El workflow de audio puede transcribir otros idiomas, pero el handoff de traducción mostrará una advertencia.

### Aparece `[CHECKPOINT:AWAITING_TRANSLATION_MAPS]`

Es una pausa esperada. Genera los mapas en la ruta indicada y ejecuta `resume.command` del checkpoint. No borres el workspace ni vuelvas a iniciar sin `-Resume`.

### WhisperX no está disponible

Con `-Backend auto`, el launcher intenta OpenAI Whisper. Revisa la advertencia y el reporte para saber qué backend se utilizó.

### CUDA se queda sin memoria

Reduce `-BatchSize`, usa un modelo menor o ejecuta con:

```powershell
-Device cpu -ComputeType int8 -Fp16 $false
```

### Los subtítulos parecen desplazados

No agregues un delay fijo antes de revisar `remux_validation.json`. El workflow de audio ya calcula y valida una transformación uniforme del timeline.

### El reproductor muestra una pista `[Local]`

Comprueba que no haya un SRT/ASS con el mismo stem junto al MKV. Los sidecars solicitados se guardan deliberadamente en `sidecars/`.

### Un lote termina con algunos archivos correctos y código de error

El modo carpeta continúa tras fallos individuales y devuelve error global si alguno falló. Revisa la lista final y el `debug/` de cada stem.

### Una ejecución anterior desapareció

Una ejecución fresca limpia `outputs/<stem>/`. Usa nombres de entrada distintos para conservar variantes o respalda el entregable antes de repetir el mismo stem.

## Validación manual recomendada

Para MKV traducido:

- inspecciona el primer minuto;
- revisa una escena de diálogo intermedia;
- revisa signos y texto posicionado;
- revisa canciones/karaoke;
- confirma que solo la pista española prevista sea predeterminada;
- prueba la variante TV-safe en el dispositivo objetivo.

Para MKV transcrito desde audio:

- compara las primeras palabras audibles con el primer cue;
- revisa un punto medio y el final;
- confirma que no aparezca una pista externa `[Local]`;
- revisa `remux_validation.json` y su desplazamiento uniforme;
- si exportaste ASS, comprueba que coincida con la pista incrustada.

Para texto/RAG:

- comprueba idioma y backend en el frontmatter;
- revisa varios rangos temporales;
- confirma que el Markdown conserve conceptos y ejemplos;
- busca duplicados, fillers excesivos o pérdidas de terminología;
- compara `clean` frente a `-Verbatim` cuando la literalidad sea importante.

## Desarrollo

- Usa Python compatible con 3.12, cuatro espacios y nombres `snake_case`.
- Usa parámetros PowerShell descriptivos en PascalCase.
- Prefiere `pathlib.Path` en Python y `-LiteralPath` para operaciones de filesystem.
- Coloca pruebas compartidas y arquitectónicas directamente en `tests/`; conserva las pruebas propias en `src/<workflow>/tests/`.
- Usa `.tmp/tests/` únicamente para archivos y workspaces temporales generados al ejecutar la suite.
- Usa fixtures sintéticos y directorios temporales; las pruebas unitarias no deben requerir medios reales.
- Mantén la lógica reutilizable en `src/shared/` y evita imports cruzados entre paquetes de workflows.
- Conserva videos, modelos, outputs, subtítulos extraídos y mapas privados fuera de Git.
- No recrees las antiguas carpetas raíz `subtitle_work/`, `translations/` ni `tools/`.

Comando final antes de entregar cambios:

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\scripts\manage_video_toolkit.ps1 `
  run-test-suite
```
