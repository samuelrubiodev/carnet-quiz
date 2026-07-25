# Database

SQLite database initializes automatically with foreign keys, WAL, schema version metadata, indexes, and transaction imports. Run `carnetquiz db check`; create backup with `carnetquiz db backup`. Version 0.1 has schema version 1. Future destructive migrations must call backup first.
