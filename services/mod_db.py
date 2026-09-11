"""
Sumair Tools Core - Disciplinary & Moderation Database Engine
============================================================
Lightweight SQLite storage managing formal server warnings, strikes,
and moderation audit records.
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger("SumairTools.ModDB")

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "moderation.db")

class ModerationDB:
    """Manages persistent infraction and warning logs."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    moderator_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
        """Adds a warning entry and returns the warning ID."""
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO warnings (guild_id, user_id, moderator_id, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (str(guild_id), str(user_id), str(moderator_id), reason, now))
            conn.commit()
            return cursor.lastrowid

    def get_warnings(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Returns all warnings for a user in a specific guild."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, moderator_id, reason, created_at
                FROM warnings
                WHERE guild_id = ? AND user_id = ?
                ORDER BY id ASC
            """, (str(guild_id), str(user_id)))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def clear_warnings(self, guild_id: int, user_id: int) -> int:
        """Clears all warnings for a user and returns number of cleared strikes."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM warnings
                WHERE guild_id = ? AND user_id = ?
            """, (str(guild_id), str(user_id)))
            conn.commit()
            return cursor.rowcount
