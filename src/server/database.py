import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Any, Tuple, List


class Database:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self, initialize_schema: Optional[str] = None) -> sqlite3.Connection:
        # allow multithreaded access in prototype (careful in production)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        if initialize_schema:
            self.init_schema(initialize_schema)
        return self.conn

    def init_schema(self, schema_path: str) -> None:
        p = Path(schema_path)
        if not p.exists():
            raise FileNotFoundError(f"schema not found: {schema_path}")
        with p.open("r", encoding="utf-8") as fh:
            sql = fh.read()
        cur = self.conn.cursor()
        cur.executescript(sql)
        self.conn.commit()

    def cursor(self):
        if self.conn is None:
            raise RuntimeError("Database not connected")
        return self.conn.cursor()

    def execute(self, sql: str, params: Tuple = ()):  # pragma: no cover - simple wrapper
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def fetchone(self, sql: str, params: Tuple = ()):  # pragma: no cover
        cur = self.execute(sql, params)
        return cur.fetchone()

    def fetchall(self, sql: str, params: Tuple = ()):  # pragma: no cover
        cur = self.execute(sql, params)
        return cur.fetchall()

    @contextmanager
    def transaction(self):
        # Start an immediate transaction to reduce concurrency races
        if self.conn is None:
            raise RuntimeError("Database not connected")
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
