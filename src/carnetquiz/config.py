from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _path(name: str, default: Path) -> Path:
    return Path(os.getenv(name, str(default))).expanduser().resolve()


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    database_path: Path
    preferred_language: str
    web_host: str
    web_port: int
    log_level: str
    questions_per_concept: int
    duplicate_threshold: float
    min_segment_seconds: float
    max_segment_seconds: float
    max_import_bytes: int

    @property
    def transcripts_dir(self) -> Path:
        return self.data_dir / "transcripts"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"


def get_settings() -> Settings:
    data_dir = _path("CARNETQUIZ_DATA_DIR", PROJECT_ROOT / "data")
    return Settings(
        data_dir=data_dir,
        database_path=_path("CARNETQUIZ_DB_PATH", data_dir / "carnetquiz.db"),
        preferred_language=os.getenv("CARNETQUIZ_PREFERRED_LANGUAGE", "es"),
        web_host=os.getenv("CARNETQUIZ_WEB_HOST", "127.0.0.1"),
        web_port=int(os.getenv("CARNETQUIZ_WEB_PORT", "8000")),
        log_level=os.getenv("CARNETQUIZ_LOG_LEVEL", "INFO"),
        questions_per_concept=int(os.getenv("CARNETQUIZ_QUESTIONS_PER_CONCEPT", "2")),
        duplicate_threshold=float(os.getenv("CARNETQUIZ_DUPLICATE_THRESHOLD", "0.88")),
        min_segment_seconds=float(os.getenv("CARNETQUIZ_MIN_SEGMENT_SECONDS", "1")),
        max_segment_seconds=float(os.getenv("CARNETQUIZ_MAX_SEGMENT_SECONDS", "18")),
        max_import_bytes=int(os.getenv("CARNETQUIZ_MAX_IMPORT_BYTES", str(5 * 1024 * 1024))),
    )


def ensure_data_dirs(settings: Settings | None = None) -> Settings:
    settings = settings or get_settings()
    for directory in (settings.data_dir, settings.transcripts_dir, settings.jobs_dir, settings.logs_dir):
        directory.mkdir(parents=True, exist_ok=True)
    return settings
