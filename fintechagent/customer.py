"""Customer records stored in SQLite."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .errors import DataError

FETCH_CUSTOMERS_SQL = "SELECT name, phone, segment FROM customers ORDER BY id;"


@dataclass(frozen=True)
class Customer:
    name: str
    mobile: str
    segment: str


@dataclass(frozen=True)
class AllCustomers:
    customers: list[Customer]

    def find(self, name: str) -> Customer | None:
        """Return the first customer whose name matches ``name`` (case-insensitive)."""
        wanted = name.strip().casefold()
        return next((c for c in self.customers if c.name.casefold() == wanted), None)

    @classmethod
    def fetch_from_db(cls, sqlite_path: str | Path) -> AllCustomers:
        """Load all customers from the SQLite database at ``sqlite_path``.

        The file must already exist: ``sqlite3.connect`` would otherwise silently
        create an empty database and fail later with a confusing error.
        """
        path = Path(sqlite_path)
        if not path.is_file():
            raise DataError(
                f"Customer database not found at '{path}'. "
                "Create it with `uv run yoyo apply --batch` (see README)."
            )
        try:
            # Read-only URI so a typo never creates or mutates a database.
            with sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True) as conn:
                rows = conn.execute(FETCH_CUSTOMERS_SQL).fetchall()
        except sqlite3.Error as exc:
            raise DataError(
                f"Could not read customers from '{path}': {exc}. "
                "Have the migrations been applied (`uv run yoyo apply --batch`)?"
            ) from exc
        return cls([Customer(name=r[0], mobile=r[1], segment=r[2]) for r in rows])
