"""Penyimpanan SQLite: memori percakapan + pengingat.

Dipakai secara sinkron (operasi kecil & cepat). Aman dipanggil dari event loop
asyncio karena setiap operasi singkat.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
from typing import Any

from . import config

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def init() -> None:
    """Buka koneksi dan buat tabel jika belum ada."""
    global _conn
    os.makedirs(os.path.dirname(config.DB_PATH) or ".", exist_ok=True)
    _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    with _lock:
        _conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER NOT NULL,
                role       TEXT    NOT NULL,
                content    TEXT    NOT NULL,
                ts         REAL    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id, id);

            CREATE TABLE IF NOT EXISTS reminders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER NOT NULL,
                user_id    INTEGER,
                message    TEXT    NOT NULL,
                due_ts     REAL    NOT NULL,
                created_ts REAL    NOT NULL,
                fired      INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_reminders_pending ON reminders(fired, due_ts);
            """
        )
        _conn.commit()


def _db() -> sqlite3.Connection:
    if _conn is None:
        raise RuntimeError("database.init() belum dipanggil")
    return _conn


# --- Memori percakapan ---------------------------------------------------

def add_message(chat_id: int, role: str, content: str) -> None:
    with _lock:
        _db().execute(
            "INSERT INTO messages (chat_id, role, content, ts) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, time.time()),
        )
        _db().commit()


def get_history(chat_id: int, limit: int) -> list[dict[str, str]]:
    """Ambil `limit` pesan terakhir, urut dari lama ke baru."""
    with _lock:
        rows = _db().execute(
            "SELECT role, content FROM messages WHERE chat_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def clear_history(chat_id: int) -> None:
    with _lock:
        _db().execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        _db().commit()


# --- Pengingat -----------------------------------------------------------

def add_reminder(chat_id: int, user_id: int | None, message: str, due_ts: float) -> int:
    with _lock:
        cur = _db().execute(
            "INSERT INTO reminders (chat_id, user_id, message, due_ts, created_ts) "
            "VALUES (?, ?, ?, ?, ?)",
            (chat_id, user_id, message, due_ts, time.time()),
        )
        _db().commit()
        return int(cur.lastrowid)


def mark_reminder_fired(reminder_id: int) -> None:
    with _lock:
        _db().execute("UPDATE reminders SET fired = 1 WHERE id = ?", (reminder_id,))
        _db().commit()


def delete_reminder(chat_id: int, reminder_id: int) -> bool:
    with _lock:
        cur = _db().execute(
            "DELETE FROM reminders WHERE id = ? AND chat_id = ? AND fired = 0",
            (reminder_id, chat_id),
        )
        _db().commit()
        return cur.rowcount > 0


def list_pending_reminders(chat_id: int) -> list[dict[str, Any]]:
    with _lock:
        rows = _db().execute(
            "SELECT id, message, due_ts FROM reminders "
            "WHERE chat_id = ? AND fired = 0 ORDER BY due_ts ASC",
            (chat_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_all_pending() -> list[dict[str, Any]]:
    """Semua pengingat yang belum berbunyi (dipakai saat startup)."""
    with _lock:
        rows = _db().execute(
            "SELECT id, chat_id, user_id, message, due_ts FROM reminders "
            "WHERE fired = 0 ORDER BY due_ts ASC"
        ).fetchall()
    return [dict(r) for r in rows]
