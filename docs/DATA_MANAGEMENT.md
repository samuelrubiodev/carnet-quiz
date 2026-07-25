# Administración de datos

CarnetQuiz ofrece borrado selectivo y reseteo total mediante el servicio común `carnetquiz.services.data_management`. CLI y web usan la misma planificación, cascadas, transacciones, copias y comprobaciones de integridad.

Estas operaciones son destructivas e irreversibles sin una copia de seguridad.

## CLI

```bash
carnetquiz data reset --dry-run
carnetquiz data reset
carnetquiz data delete video VIDEO_ID --dry-run
carnetquiz data delete transcript VIDEO_ID --cascade
carnetquiz data delete job JOB_ID
carnetquiz data delete concept CONCEPT_ID
carnetquiz data delete question QUESTION_ID
carnetquiz data delete attempt ATTEMPT_ID
```

`data reset` elimina respuestas, intentos, preguntas, conceptos, trabajos, segmentos y vídeos. Conserva esquema SQLite, código, configuración, estáticos, `tests/`, entorno virtual y copias de seguridad. Mantiene la instalación inicializada y borra archivos de transcripciones y directorios de trabajos.

El reseteo interactivo exige escribir exactamente:

```text
RESET CARNETQUIZ
```

La forma no interactiva exige ambas opciones:

```bash
carnetquiz data reset --yes --confirm "RESET CARNETQUIZ"
```

Los borrados selectivos muestran un plan y usan confirmación negativa por defecto. `video` siempre elimina sus dependencias. `transcript` conserva el vídeo; sin `--cascade` se bloquea si existen trabajos, conceptos o preguntas derivados. `job`, `concept` y `question` eliminan intentos afectados; `attempt` solo elimina sus respuestas y recalcula estadísticas.

`--dry-run` no modifica SQLite ni el sistema de archivos. `--json` no mezcla prompts ni texto, y exige `--yes` para una operación real. Las copias consistentes se guardan en `data-backups/` fuera del directorio de datos. `--no-backup` las omite y genera una advertencia.

## Seguridad

Solo se eliminan rutas registradas o hijos directos de los directorios configurados de transcripciones y trabajos. Se rechazan rutas con `..`, fuera de esas raíces o enlaces simbólicos. Cada operación valida `foreign_key_check` e `integrity_check`; un fallo de limpieza de archivos devuelve estado incompleto y código de salida distinto de cero.

La web local expone **Administración de datos** en `/admin/data`. Las previsualizaciones y operaciones destructivas usan `POST`; no acepta rutas del sistema de archivos.
