# CarnetQuiz

Aplicación local Python para estudiar teoría de conducción con preguntas trazables a transcripciones de YouTube. No llama modelos, no pide API keys y no descarga vídeo/audio para buscar subtítulos.

CarnetQuiz está preparado para trabajar con agentes de IA locales o asistentes de programación como Pi, Claude Code y Codex. El agente analiza los trabajos, genera conceptos y preguntas fundamentados únicamente en la transcripción, y utiliza la CLI o el MCP para validar e importar resultados.

## Requisitos e instalación

Python 3.11+, `yt-dlp` en `PATH` solo para YouTube.

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/carnetquiz init
```

Variables opcionales: copiar `.env.example` y exportarlas desde shell. `CARNETQUIZ_DATA_DIR`, `CARNETQUIZ_DB_PATH`, idioma, host, puerto y umbrales están documentados allí.

## Demo vertical

```bash
.venv/bin/carnetquiz demo
.venv/bin/carnetquiz serve
# abrir http://127.0.0.1:8000
```

Demo crea vídeo, transcripción, conceptos y preguntas dentro de servicios validados. Creá test desde interfaz; resultados quedan en SQLite.

## CLI

```bash
carnetquiz doctor
carnetquiz video add URL
carnetquiz transcript fetch VIDEO_ID
carnetquiz transcript import VIDEO_ID archivo.vtt
carnetquiz transcript show VIDEO_ID --until 30m
carnetquiz job create VIDEO_ID --until 30m
carnetquiz job create VIDEO_ID --from 30m --until 60m
carnetquiz job create VIDEO_ID --from 1h --until 01:30:00
carnetquiz job validate JOB_ID
carnetquiz job commit JOB_ID --yes
carnetquiz questions stats
carnetquiz db check
carnetquiz db backup
carnetquiz data reset --dry-run
carnetquiz data reset
carnetquiz data delete video VIDEO_ID --dry-run
carnetquiz data delete transcript VIDEO_ID --cascade
carnetquiz data delete job JOB_ID
carnetquiz data delete concept CONCEPT_ID
carnetquiz data delete question QUESTION_ID
carnetquiz data delete attempt ATTEMPT_ID
```

`data reset` exige escribir exactamente `RESET CARNETQUIZ` en modo interactivo o usar `--yes --confirm "RESET CARNETQUIZ"`. Los borrados selectivos exigen confirmación; en JSON requieren `--yes`. Estas operaciones son irreversibles sin una copia de seguridad. Crean copias consistentes fuera de `data/` salvo que se indique expresamente `--no-backup`. Ver [docs/DATA_MANAGEMENT.md](docs/DATA_MANAGEMENT.md).

`video add` consulta metadatos con `yt-dlp`; `transcript fetch` prioriza subtítulos manuales españoles, automáticos españoles, luego idioma original. Importación manual admite VTT, SRT, JSON3 y `.txt` segmentado: `00:00:00 --> 00:00:05 | texto`. Todos los comandos aceptan ayuda con `--help`; consultas principales aceptan `--json`.

## Uso como Skill con agentes CLI

CarnetQuiz se usa mediante una **Skill** que guía al agente mientras ejecuta la CLI. No es necesario pedirle al agente que genere una estructura ni copiar prompts manualmente.

### Ubicación de Skills

- **Universal:** `.agents/skills/process-video/SKILL.md`. Es la Skill principal para Pi, Codex y otros agentes CLI compatibles.
- **Claude Code:** `.claude/skills/carnet-quizvideo/SKILL.md`. Adaptador de Claude Code con comando `/process-video`.
- **Reglas generales:** [AGENTS.md](AGENTS.md).
- **Reglas específicas de Claude Code:** [CLAUDE.md](CLAUDE.md).

Ambas Skills ejecutan el mismo flujo: comprobar entorno, añadir o localizar vídeo, obtener subtítulos, crear un trabajo, leer únicamente el trabajo actual, generar JSON, validar, reparar como máximo una vez e importar.

### Pi, Codex y otros agentes CLI

Inicia el agente desde la raíz del proyecto y pedile que use la Skill universal:

```text
Lee y sigue .agents/skills/process-video/SKILL.md.
Procesa este vídeo de YouTube hasta 20m:
https://www.youtube.com/watch?v=VIDEO_ID
```

También puedes indicar peticiones equivalentes en lenguaje natural:

```text
Procesa https://www.youtube.com/watch?v=VIDEO_ID hasta 30 minutos con CarnetQuiz.
Procesa https://www.youtube.com/watch?v=VIDEO_ID desde el minuto 30 hasta el minuto 60.
Continúa este vídeo desde el minuto 30 hasta el 60.
```

La Skill resuelve `VIDEO_URL`, `START_TIME` y `END_TIME`. Si solo se indica el límite final, `START_TIME=0m`. Las fronteras son `[inicio, final)`: `segment.start_seconds >= inicio` y `segment.start_seconds < final`.

El agente debe ejecutar el flujo definido por la Skill, no editar SQLite ni usar conocimiento externo. La transcripción del trabajo actual es la única fuente factual.

### Claude Code

Desde la raíz del proyecto, usá el comando de la Skill:

```text
/process-video https://www.youtube.com/watch?v=VIDEO_ID 30m
```

El límite de tiempo es opcional; si se omite, la Skill usa `30m`.

### Flujo CLI ejecutado por la Skill

La Skill ejecuta comandos equivalentes a:

```bash
carnetquiz doctor
carnetquiz video add URL
carnetquiz transcript fetch VIDEO_ID
carnetquiz job create VIDEO_ID --until 30m
carnetquiz job create VIDEO_ID --from 30m --until 60m
carnetquiz job validate JOB_ID
carnetquiz job commit JOB_ID --yes
```

Durante el procesamiento, el agente escribe únicamente en el trabajo actual:

```text
data/jobs/JOB_ID/concepts.json
data/jobs/JOB_ID/questions.json
data/jobs/JOB_ID/review.json
```

Cada trabajo contiene configuración, esquemas JSON, transcripción recortada e informe de validación. Las preguntas deben citar segmentos y tiempos, tener una única respuesta válida y basarse solo en `transcript.json`.

No se requieren APIs de IA de pago ni claves externas. El agente aporta el razonamiento; CarnetQuiz aporta CLI, validación determinista, SQLite e importación transaccional. El flujo completo está documentado en [docs/PI_WORKFLOW.md](docs/PI_WORKFLOW.md); MCP está disponible como alternativa en [docs/MCP.md](docs/MCP.md).

## Trabajo manual

Ver [docs/PI_WORKFLOW.md](docs/PI_WORKFLOW.md). Trabajo deja `request.json`, recorte `transcript.json`, schemas locales, entradas JSON e informe de validación. Validador rechaza referencias fuera de rango, segmentos faltantes, preguntas duplicadas, opciones repetidas, HTML, estructuras inválidas y respuestas correctas ausentes. Importación es transaccional; trabajo parcialmente válido puede importar preguntas válidas.

## Web

`carnetquiz serve --port 8000` inicia FastAPI local. La creación de trabajos acepta `Desde` y `Hasta`, con inicio cero por defecto, y muestra cada intervalo como `00:30:00 – 01:00:00`. Los solapamientos se permiten y generan advertencia. La creación de tests puede filtrar por intervalo; sin filtro mantiene el banco acumulativo del vídeo.

Incluye inicio, vídeos, transcripciones, trabajos, creación/realización de test, resultados, estadísticas y **Administración de datos**. Esta última sección muestra cantidades, previsualiza planes y ejecuta borrados solo mediante `POST`; el reseteo exige `RESET CARNETQUIZ`. Selección: aleatoria, equilibrada, nuevas, fallos, inteligente y examen. Opciones se barajan al presentar sin perder respuesta correcta.

## MCP

`carnetquiz mcp` abre transporte stdio. Ver [docs/MCP.md](docs/MCP.md). MCP reutiliza mismos servicios CLI. CLI sigue funcionando sin MCP.

## Calidad

```bash
.venv/bin/pytest
.venv/bin/ruff check src tests
carnetquiz doctor
carnetquiz db check
```

## Límites conocidos

- YouTube puede bloquear subtítulos, vídeo privado/restringido, o no proveerlos; mensaje se devuelve desde `yt-dlp`.
- Subtítulos JSON3 dependen de formato de YouTube.
- Sesiones de test en curso viven en memoria web; respuestas terminadas sí persisten.
- Esquema v1 no incluye migraciones posteriores; futuras migraciones deben crear copia antes de cambios destructivos.
