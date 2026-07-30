from pathlib import Path
import sqlite3

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "sql"
DB_PATH = DB_DIR / "mes.db"


def database_exists() -> bool:
    return DB_PATH.exists()

def init_db_dir():
    if not DB_DIR.exists():
        DB_DIR.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    init_db_dir()
    if not database_exists():
        raise FileNotFoundError(f"SQLite 데이터베이스 파일을 찾을 수 없습니다: {DB_PATH}")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def fetch_dataframe(sql: str, params: tuple = ()) -> pd.DataFrame:
    with get_connection() as connection:
        return pd.read_sql_query(sql, connection, params=params)


def fetch_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    with get_connection() as connection:
        cursor = connection.execute(sql, params)
        return cursor.fetchone()


def fetch_all(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    with get_connection() as connection:
        cursor = connection.execute(sql, params)
        return cursor.fetchall()

def execute_commit(sql: str, params: tuple = ()) -> int:
    with get_connection() as connection:
        cursor = connection.execute(sql, params)
        connection.commit()
        return cursor.rowcount
    
    
