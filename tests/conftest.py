from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    monkeypatch.setenv("CARNETQUIZ_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("CARNETQUIZ_DB_PATH", str(tmp_path / "data" / "carnetquiz.db"))
