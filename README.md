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
carnetquiz job validate JOB_ID
carnetquiz job commit JOB_ID --yes
carnetquiz questions stats
carnetquiz db check
carnetquiz db backup
```

`video add` consulta metadatos con `yt-dlp`; `transcript fetch` prioriza subtítulos manuales españoles, automáticos españoles, luego idioma original. Importación manual admite VTT, SRT, JSON3 y `.txt` segmentado: `00:00:00 --> 00:00:05 | texto`. Todos los comandos aceptan ayuda con `--help`; consultas principales aceptan `--json`.

## Uso con agentes de IA

El proyecto está diseñado para agentes como **Pi**, **Claude Code**, **Codex** y otros clientes compatibles con MCP. La CLI es la fuente de verdad; el agente no debe editar SQLite directamente.

Flujo recomendado:

```bash
carnetquiz video add URL
carnetquiz transcript fetch VIDEO_ID
carnetquiz job create VIDEO_ID --until 30m
```

Después, indicá al agente:

> Lee `request.json`, `transcript.json` y los esquemas JSON del trabajo. Completa `concepts.json`, `questions.json` y `review.json` usando únicamente la transcripción. Cita siempre segmentos y tiempos. No uses conocimiento externo ni edites SQLite. Ejecuta la validación y realiza como máximo una revisión y una reparación.

El agente debe finalizar con:

```bash
carnetquiz job validate JOB_ID
carnetquiz job commit JOB_ID --yes
```

Cada trabajo contiene configuración, esquemas JSON, transcripción recortada, archivos de salida e informe de validación. Las reglas para agentes están en [AGENTS.md](AGENTS.md), el flujo detallado en [docs/PI_WORKFLOW.md](docs/PI_WORKFLOW.md) y la integración MCP en [docs/MCP.md](docs/MCP.md).

No se requieren APIs de IA de pago ni claves externas. El agente puede ejecutarse con el modelo y las herramientas locales disponibles en el entorno.

## Trabajo manual

Ver [docs/PI_WORKFLOW.md](docs/PI_WORKFLOW.md). Trabajo deja `request.json`, recorte `transcript.json`, schemas locales, entradas JSON e informe de validación. Validador rechaza referencias fuera de rango, segmentos faltantes, preguntas duplicadas, opciones repetidas, HTML, estructuras inválidas y respuestas correctas ausentes. Importación es transaccional; trabajo parcialmente válido puede importar preguntas válidas.

## Web

`carnetquiz serve --port 8000` inicia FastAPI local. Incluye inicio, vídeos, transcripciones, trabajos, creación/realización de test, resultados y estadísticas. Selección: aleatoria, equilibrada, nuevas, fallos, inteligente y examen. Opciones se barajan al presentar sin perder respuesta correcta.

## MCP

`carnetquiz mcp` abre transporte stdio. Ver [docs/MCP.md](docs/MCP.md). MCP reutiliza mismos servicios CLI. CLI sigue funcionando sin MCP.

## Calidad

```bash
.venv/bin/pytest
.venv/bin/ruff check src tests
```

## Límites conocidos

- YouTube puede bloquear subtítulos, vídeo privado/restringido, o no proveerlos; mensaje se devuelve desde `yt-dlp`.
- Subtítulos JSON3 dependen de formato de YouTube.
- Sesiones de test en curso viven en memoria web; respuestas terminadas sí persisten.
- Esquema v1 no incluye migraciones posteriores; futuras migraciones deben crear copia antes de cambios destructivos.
