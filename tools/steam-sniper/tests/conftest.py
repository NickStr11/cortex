from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Patch db.DB_PATH to a temp file so tests don't touch real data."""
    db_path = tmp_path / "test_sniper.db"
    import db

    monkeypatch.setattr(db, "DB_PATH", db_path)
    return db_path
