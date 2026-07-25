# CarnetQuiz

Aplicación local Python para estudiar teoría de conducción con preguntas trazables a transcripciones de YouTube. No llama modelos, no pide API keys y no descarga vídeo/audio para buscar subtítulos.

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

## Trabajo manual

Ver [docs/PI_WORKFLOW.md](docs/PI_WORKFLOW.md). Trabajo deja `request.json`, recorte `transcript.json`, contexto, schemas locales, entradas JSON, informe validación. Validador rechaza referencias fuera de rango, segmentos faltantes, preguntas duplicadas, opciones repetidas, HTML, estructuras inválidas y respuestas correctas ausentes. Importación es transaccional; trabajo parcialmente válido puede importar preguntas válidas.

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
