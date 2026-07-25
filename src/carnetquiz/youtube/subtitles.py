from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .metadata import VideoMetadata, yt_dlp_available


def choose_subtitle(metadata: VideoMetadata, preferred: str = "es", language: str | None = None) -> tuple[str, bool]:
    requested = language or preferred
    choices = [(metadata.subtitles, False), (metadata.automatic_captions, True)]
    for target in (requested, requested.split("-")[0], metadata.language or ""):
        for catalogue, automatic in choices:
            matching = next((key for key in catalogue if key.lower() == target.lower()), None)
            if matching:
                return matching, automatic
    for catalogue, automatic in choices:
        if catalogue:
            return next(iter(catalogue)), automatic
    raise RuntimeError("Vídeo sin subtítulos manuales ni automáticos disponibles")


def download_subtitles(metadata: VideoMetadata, destination: Path, preferred: str = "es", language: str | None = None, timeout: int = 60) -> tuple[Path, str, bool]:
    if not yt_dlp_available():
        raise RuntimeError("yt-dlp no está instalado o no está en PATH")
    selected, automatic = choose_subtitle(metadata, preferred, language)
    with tempfile.TemporaryDirectory() as temporary:
        template = str(Path(temporary) / "subtitle.%(ext)s")
        command = ["yt-dlp", "--skip-download", "--no-playlist", "--sub-langs", selected, "--sub-format", "vtt", "-o", template]
        command.append("--write-auto-subs" if automatic else "--write-subs")
        command.append(metadata.url)
        result = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
        files = list(Path(temporary).glob("*.vtt"))
        if result.returncode or not files:
            detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "archivo no creado"
            raise RuntimeError(f"yt-dlp no pudo descargar subtítulos: {detail}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(files[0], destination)
    return destination, selected, automatic
