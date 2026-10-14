import os
import sqlite3

from settings import DB_PATH


def database_exists():
    return os.path.exists(DB_PATH)


def get_connection():
    if not database_exists():
        raise FileNotFoundError("Database not found at " + DB_PATH)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def run_query(sql, params=()):
    connection = get_connection()
    try:
        rows = connection.execute(sql, params).fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]
