# Pendientes

## 1. Limpiador manual de ruido de fondo

Explorar e implementar un flujo de limpieza manual de ruido de fondo antes de `video-voice-cleaner`, idealmente mediante una integracion MCP con Audacity o mediante una CLI reproducible. El objetivo es permitir una primera pasada controlada para casos con ruido ambiental fuerte, evitando procesamientos agresivos que deformen la voz.

## 2. Skills ejecutables para scripts FFmpeg manuales

Convertir los scripts y comandos FFmpeg hechos a mano en skills locales ejecutables, con instrucciones claras, parametros esperados, validaciones y artefactos de salida. Cada skill debe poder guiar al agente para ejecutar el flujo correcto sin depender de conocimiento informal o pasos manuales sueltos.

### 2. Audio voice cleaner en GPU

video-voice-cleaner usa esta cadena de audio: arnndn, afftdn ,anlmdn, agate, equalizer, deesser, acompressor, alimiter, loudnorm, aresample, codificación flac; filtros que solo ofrece FFMPEG en CPU, En tu FFmpeg esos filtros aparecen como filtros de audio A->A, no como filtros CUDA/OpenCL. Los filtros CUDA disponibles en tu FFmpeg son de video (scale_cuda, overlay_cuda, yadif_cuda, etc.), no sirven para esta cadena de limpieza vocal.

Para una alternativa realmente GPU habría que integrar otro backend de denoise/voice enhancement basado en PyTorch/CUDA, pero eso sería otro perfil/flujo y habría que cuidarlo mucho para no volver la voz robótica.
