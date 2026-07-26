# MCP local server

Start stdio server:

```bash
carnetquiz mcp
```

Example client configuration:

```json
{"mcpServers":{"carnetquiz":{"command":"/path/to/.venv/bin/carnetquiz","args":["mcp"]}}}
```

Tools: `list_videos`, `get_video`, `add_video`, `fetch_transcript`, `get_transcript_range`, `create_generation_job`, `list_jobs`, `get_job_context`, `submit_concepts`, `submit_questions`, `submit_review`, `validate_job`, `commit_job`, `get_validation_report`, `list_questions`, `get_question_statistics`.

`create_generation_job` mantiene clientes anteriores:

```text
create_generation_job(video_id, until, start="0s")
```

`start` es opcional y crea el intervalo `[start, until)`. No descarga otra transcripción.

Server exposes no arbitrary commands, paths, SQL, system files, or database deletion. If client adapter fails, use CLI; it is canonical.
