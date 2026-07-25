# Architecture

CLI, web, and MCP call shared `services`. Services use constrained repositories for SQLite. YouTube layer calls `yt-dlp` only with `--skip-download`; parser and normalizer are deterministic. Jobs are filesystem artifacts under `data/jobs`, validated before one transaction imports concepts/questions. Web retains in-progress test order in process memory; completed answers persist in SQLite.

`services.data_management` is the only destructive-data layer. CLI and web build and execute the same `DeletionPlan`; it owns explicit dependency deletion, SQLite transactions and integrity checks, consistent backups, and protected cleanup under transcript/job roots. MCP exposes no destructive operation.
