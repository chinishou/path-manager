"""
SQLite-based compiled schema storage.
"""

import json
import sqlite3
from pathlib import Path
from typing import Iterator

from .base import CompiledStore


class SQLiteStore(CompiledStore):
    """
    SQLite-based storage implementation.

    Uses immutable=1 mode for safe concurrent reads on NFS.
    """

    def __init__(self, db_path: str | Path):
        """
        Initialize SQLite store.

        Args:
            db_path: Path to SQLite database file

        Note:
            Opens database in immutable mode: file:path?immutable=1
            This is safe for concurrent reads on NFS.
        """
        db_path = Path(db_path)
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

        # Open in immutable mode for safe NFS concurrent reads
        uri = f"file:{db_path.absolute()}?immutable=1"
        self.conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def get_kind(self, name: str) -> dict | None:
        """Get kind definition by name."""
        row = self.conn.execute(
            "SELECT template, fields_json FROM kinds WHERE name = ?",
            (name,)
        ).fetchone()

        if not row:
            return None

        return {
            "template": row["template"],
            "fields": json.loads(row["fields_json"])
        }

    def get_dir(self, name: str) -> dict | None:
        """Get directory definition by name."""
        row = self.conn.execute(
            "SELECT template, fields_json FROM dirs WHERE name = ?",
            (name,)
        ).fetchone()

        if not row:
            return None

        return {
            "template": row["template"],
            "fields": json.loads(row["fields_json"])
        }

    def get_field(self, name: str) -> dict | None:
        """Get field definition by name."""
        row = self.conn.execute(
            "SELECT regex, example FROM fields WHERE name = ?",
            (name,)
        ).fetchone()

        if not row:
            return None

        return {
            "regex": row["regex"],
            "example": row["example"]
        }

    def iter_all_kinds(self) -> Iterator[str]:
        """Iterate over all kind names."""
        cursor = self.conn.execute("SELECT name FROM kinds ORDER BY name")
        for row in cursor:
            yield row["name"]

    def get_ambiguities(self) -> dict[str, list[str]]:
        """Get ambiguity mapping."""
        result = {}
        cursor = self.conn.execute("SELECT pattern, kind_names FROM ambiguities")

        for row in cursor:
            result[row["pattern"]] = json.loads(row["kind_names"])

        return result

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


def create_schema(db_path: str | Path):
    """
    Create SQLite schema for compiled storage.

    Args:
        db_path: Path where database will be created
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create with write mode
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fields (
            name TEXT PRIMARY KEY,
            regex TEXT NOT NULL,
            example TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kinds (
            name TEXT PRIMARY KEY,
            template TEXT NOT NULL,
            fields_json TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dirs (
            name TEXT PRIMARY KEY,
            template TEXT NOT NULL,
            fields_json TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ambiguities (
            pattern TEXT PRIMARY KEY,
            kind_names TEXT NOT NULL
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kinds_template ON kinds(template)")

    conn.commit()
    conn.close()

    # Set file to read-only (444)
    db_path.chmod(0o444)
