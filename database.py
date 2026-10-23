"""파이썬 내장 SQLite 저장소. 사용자 테이블은 entries 하나뿐이다."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(os.environ.get("GUESTBOOK_DB_PATH", Path(__file__).parent / "data" / "guestbook.sqlite3"))
PAGE_SIZE = 10
MAX_ENTRIES = 1000


def connect():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect()) as connection, connection:
        # INTEGER PRIMARY KEY는 별도의 시퀀스 테이블을 만들지 않는다.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 20),
                content TEXT NOT NULL CHECK(length(content) BETWEEN 1 AND 1000),
                created_at TEXT NOT NULL
                    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
        """)


def list_entries(page=1):
    with closing(connect()) as connection:
        records = connection.execute(
            "SELECT id, name, content, created_at FROM entries "
            "ORDER BY id DESC LIMIT ? OFFSET ?",
            (PAGE_SIZE, (page - 1) * PAGE_SIZE),
        ).fetchall()
        return [dict(record) for record in records]


def count_entries():
    with closing(connect()) as connection:
        return connection.execute("SELECT COUNT(*) FROM entries").fetchone()[0]


def add_entry(entry):
    with closing(connect()) as connection, connection:
        # 건수 확인과 저장을 한 트랜잭션으로 처리해 동시 요청도 제한을 지킨다.
        connection.execute("BEGIN IMMEDIATE")
        count = connection.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        if count >= MAX_ENTRIES:
            raise ValueError("방명록이 가득 찼습니다. 최대 1,000개까지 저장할 수 있습니다.")
        cursor = connection.execute(
            "INSERT INTO entries (name, content) VALUES (?, ?)",
            (entry.name, entry.content),
        )
        record = connection.execute(
            "SELECT id, name, content, created_at FROM entries WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return dict(record)
