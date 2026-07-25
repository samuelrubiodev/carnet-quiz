# Architecture

CLI, web, and MCP call shared `services`. Services use constrained repositories for SQLite. YouTube layer calls `yt-dlp` only with `--skip-download`; parser and normalizer are deterministic. Jobs are filesystem artifacts under `data/jobs`, validated before one transaction imports concepts/questions. Web retains in-progress test order in process memory; completed answers persist in SQLite.
