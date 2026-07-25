# Database

SQLite database initializes automatically with foreign keys, WAL, schema version metadata, indexes, and transaction imports. Run `carnetquiz db check`; create backup with `carnetquiz db backup`. Database backups use SQLite Online Backup, so WAL data is included consistently.

`carnetquiz data reset` deletes rows in dependency order inside one transaction, preserves schema version 1 and resets autoincrement sequences. Before real destructive operations it creates a backup in `data-backups/`; reset also backs up transcript files and job directories with a JSON manifest. Future destructive migrations must call backup first.
