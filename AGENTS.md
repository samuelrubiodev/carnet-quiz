# CarnetQuiz agent rules

- Never edit SQLite directly. Use `carnetquiz` CLI or MCP tools.
- Use only job transcript. Never add external driving knowledge.
- Every concept and question must cite transcript segment IDs and times.
- Respect job-local JSON schemas and validate before import.
- At most one review and one optional repair. Do not loop regeneration.
- Do not write outside repository or a job directory.
- Import only with `carnetquiz job commit JOB_ID` after validation.
