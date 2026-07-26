# Flujo manual de agentes

Crear trabajo hasta 30 minutos, equivalente a `0m–30m`:

```bash
carnetquiz video add URL
carnetquiz transcript fetch VIDEO_ID
carnetquiz job create VIDEO_ID --until 30m
```

Procesar intervalo posterior sin descargar otra vez la transcripción:

```bash
carnetquiz job create VIDEO_ID --from 30m --until 60m
carnetquiz job create VIDEO_ID --from 1h --until 01:30:00
```

`--from` y `--until` aceptan segundos, `m`, `h` y formatos como `01:30:00`. El intervalo usa frontera inicial inclusiva y final exclusiva. El segmento se incluye cuando `start_seconds >= inicio` y `start_seconds < final`. `last_processed_seconds` no decide el inicio automáticamente.

La Skill `.agents/skills/process-video/SKILL.md` resuelve `VIDEO_URL`, `START_TIME` y `END_TIME`, conserva esos valores durante todo el flujo y procesa solo el `transcript.json` del trabajo creado. Una transcripción válida existente se reutiliza; no se descarga para cada intervalo.

Después, el agente debe:

1. Leer `request.json`, `transcript.json` y schemas del trabajo actual.
2. Completar `concepts.json`.
3. Completar `questions.json`.
4. Completar `review.json`.
5. Ejecutar `carnetquiz job validate JOB_ID`.
6. Corregir elementos rechazados una sola vez como máximo.
7. Validar otra vez si hubo reparación.
8. Ejecutar `carnetquiz job commit JOB_ID --yes` solo si la validación lo permite.

No leer otro transcript, editar SQLite, repetir generación completa ni importar antes de validar. Los trabajos solapados se permiten, pero sus preguntas idénticas son rechazadas por validación. El banco importado es acumulativo: un test sin filtro hasta `60m` puede seleccionar preguntas importadas desde `0m–30m` y `30m–60m`.

El agente no debe añadir conocimiento externo. Si la evidencia es insuficiente, omite el concepto o pregunta.
