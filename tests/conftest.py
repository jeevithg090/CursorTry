import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MIGRATION = ROOT / "migrations" / "20250215_01_xDH6D-init.sql"


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """A SQLite DB built from the real migration (same schema + seed data)."""
    path = tmp_path / "bank.sqlite"
    with sqlite3.connect(path) as conn:
        conn.executescript(MIGRATION.read_text())
    return path


@pytest.fixture
def products_dir() -> Path:
    return ROOT / "products"
