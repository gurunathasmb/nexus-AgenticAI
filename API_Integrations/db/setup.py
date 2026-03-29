import os
import sqlite3
from typing import Generator

import pyodbc

# SQL Server connection string (Windows / servers with ODBC Driver 17)
CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"
    "DATABASE=nexus_agent_db;"
    "Trusted_Connection=yes;"
)


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _sqlite_path() -> str:
    custom = os.getenv("CHAT_SQLITE_PATH", "").strip()
    if custom:
        return custom
    return os.path.join(_repo_root(), "API_Integrations", "nexus_chat.sqlite")


def _ensure_sqlite_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ChatSessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS ChatMessages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            sender_agent TEXT,
            text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES ChatSessions(id)
        );
        """
    )
    conn.commit()


def _open_sqlite() -> sqlite3.Connection:
    path = _sqlite_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    _ensure_sqlite_schema(conn)
    return conn


def _open_sql_server() -> pyodbc.Connection:
    return pyodbc.connect(CONNECTION_STRING)


def using_sqlite() -> bool:
    return os.environ.get("_NEXUS_CHAT_USING_SQLITE") == "1"


def _resolve_mode() -> str:
    m = os.getenv("NEXUS_CHAT_BACKEND", "auto").strip().lower()
    if m in ("sqlite", "sql", "mssql", "auto"):
        return m
    return "auto"


def get_db_connection():
    """Chat persistence: SQL Server when available, else SQLite in API_Integrations/."""
    mode = _resolve_mode()

    if mode == "sqlite":
        conn = _open_sqlite()
        os.environ["_NEXUS_CHAT_USING_SQLITE"] = "1"
        return conn

    if mode in ("mssql", "sql"):
        os.environ["_NEXUS_CHAT_USING_SQLITE"] = "0"
        try:
            return _open_sql_server()
        except Exception as e:
            raise RuntimeError(f"Database connection failed: {e}") from e

    try:
        conn = _open_sql_server()
        os.environ["_NEXUS_CHAT_USING_SQLITE"] = "0"
        return conn
    except Exception:
        conn = _open_sqlite()
        os.environ["_NEXUS_CHAT_USING_SQLITE"] = "1"
        return conn


def get_db() -> Generator:
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()


def test_connection():
    conn = get_db_connection()
    cursor = conn.cursor()
    if using_sqlite():
        cursor.execute("SELECT 1")
        print(f"✅ Chat DB (SQLite): {_sqlite_path()}")
    else:
        cursor.execute("SELECT DB_NAME()")
        db_name = cursor.fetchone()[0]
        print(f"✅ Connected to database: {db_name}")
    conn.close()


if __name__ == "__main__":
    test_connection()
