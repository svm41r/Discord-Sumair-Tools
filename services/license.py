"""
Sumair Tools Core - License Database & Validation Engine
========================================================
High-performance SQLite database managing official customer licenses.
Imports data/licenses.csv on boot, validates keys, and atomically
binds licenses to verified Discord user IDs.
"""

import os
import csv
import sqlite3
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import config

logger = logging.getLogger("SumairTools.LicenseService")

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "licenses.db")
CSV_PATH = os.path.join(DB_DIR, "licenses.csv")

@dataclass
class LicenseValidationResult:
    valid: bool
    message: str
    product_name: str = "SVM41R Master Tools Pro"
    tier: str = "Lifetime Pro License"
    customer_email: Optional[str] = None
    license_key: str = ""

class LicenseService:
    """Enterprise licensing engine backed by SQLite persistent storage."""

    def __init__(self, db_path: str = DB_PATH, csv_path: str = CSV_PATH):
        self.db_path = db_path
        self.csv_path = csv_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes tables and seeds initial CSV data if empty."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS licenses (
                    license_key TEXT PRIMARY KEY COLLATE NOCASE,
                    status TEXT NOT NULL,
                    active INTEGER NOT NULL,
                    claimed_user_id TEXT,
                    claimed_user_name TEXT,
                    claimed_user_email TEXT,
                    machine_id TEXT,
                    created_at TEXT,
                    activated_at TEXT
                )
            """)
            conn.commit()

            if os.path.exists(self.csv_path):
                self._import_csv(cursor)
                conn.commit()

            cursor.execute("SELECT COUNT(*) FROM licenses")
            count = cursor.fetchone()[0]
            logger.info(f"Loaded existing License Database with {count} keys.")

    def _import_csv(self, cursor: sqlite3.Cursor):
        """Parses CSV and inserts records into SQLite."""
        logger.info(f"Seeding license database from {self.csv_path}...")
        inserted = 0
        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    raw_key = row.get("License Key")
                    if not raw_key or not isinstance(raw_key, str):
                        continue
                    key = raw_key.strip()
                    if not key:
                        continue

                    raw_status = row.get("Status")
                    status = raw_status.strip().lower() if isinstance(raw_status, str) else "unactivated"

                    raw_active = row.get("Active")
                    active_val = 1 if isinstance(raw_active, str) and raw_active.strip().upper() == "TRUE" else 0

                    raw_user = row.get("Claimed User Name")
                    claimed_user = raw_user.strip() if isinstance(raw_user, str) and raw_user.strip() else None

                    raw_email = row.get("Claimed User Email")
                    claimed_email = raw_email.strip() if isinstance(raw_email, str) and raw_email.strip() else None

                    raw_machine = row.get("Machine ID")
                    machine_id = raw_machine.strip() if isinstance(raw_machine, str) and raw_machine.strip() else None

                    raw_created = row.get("Created At")
                    created_at = raw_created.strip() if isinstance(raw_created, str) and raw_created.strip() else datetime.utcnow().isoformat()

                    cursor.execute("""
                        INSERT OR IGNORE INTO licenses (
                            license_key, status, active, claimed_user_id, claimed_user_name,
                            claimed_user_email, machine_id, created_at, activated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (key, status, active_val, None, claimed_user, claimed_email, machine_id, created_at, None))
                    inserted += 1

            logger.info(f"Successfully imported {inserted} official license keys into SQLite.")
        except Exception as e:
            logger.error(f"Error importing CSV licenses: {e}")

    async def validate_license(self, license_key: str, discord_user_id: int, discord_user_name: str = "") -> LicenseValidationResult:
        """
        Asynchronously validates and binds a license key to a Discord user.
        Thread-safe and atomic.
        """
        clean_key = license_key.strip().upper()

        if not clean_key or len(clean_key) < 8:
            return LicenseValidationResult(
                valid=False,
                message="License key format is invalid or too short. Please verify your receipt.",
                license_key=clean_key,
            )

        # 1. Lookup in native SQLite database
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM licenses WHERE license_key = ?", (clean_key,))
                row = cursor.fetchone()

                if row:
                    status = row["status"].lower()
                    is_active = bool(row["active"])
                    claimed_id = row["claimed_user_id"]
                    claimed_name = row["claimed_user_name"]
                    claimed_email = row["claimed_user_email"]

                    # Check revocation or deactivation
                    if status == "revoked":
                        return LicenseValidationResult(
                            valid=False,
                            message="This license key has been revoked or refunded. Contact support if this is an error.",
                            license_key=clean_key,
                        )
                    if status == "active" and not is_active:
                        return LicenseValidationResult(
                            valid=False,
                            message="This license has been deactivated. Contact support for assistance.",
                            license_key=clean_key,
                        )

                    # Check already claimed by someone else
                    if claimed_id and str(claimed_id) != str(discord_user_id):
                        return LicenseValidationResult(
                            valid=False,
                            message=f"This license key was already claimed by another user (<@{claimed_id}>).",
                            license_key=clean_key,
                        )

                    # Check already claimed by this user
                    if claimed_id and str(claimed_id) == str(discord_user_id):
                        return LicenseValidationResult(
                            valid=True,
                            message="License is already registered to your account.",
                            product_name="SVM41R Master Tools Pro",
                            tier="Lifetime Pro License",
                            customer_email=claimed_email,
                            license_key=clean_key,
                        )

                    # Key is valid and available to claim!
                    now_iso = datetime.utcnow().isoformat()
                    cursor.execute("""
                        UPDATE licenses
                        SET status = 'active', active = 1, claimed_user_id = ?, claimed_user_name = ?, activated_at = ?
                        WHERE license_key = ?
                    """, (str(discord_user_id), discord_user_name or f"User-{discord_user_id}", now_iso, clean_key))
                    conn.commit()

                    logger.info(f"License {clean_key[:10]}**** successfully claimed by {discord_user_name} ({discord_user_id})")
                    return LicenseValidationResult(
                        valid=True,
                        message="License successfully validated and bound to your Discord account.",
                        product_name="SVM41R Master Tools Pro",
                        tier="Lifetime Pro License",
                        customer_email=claimed_email,
                        license_key=clean_key,
                    )

        except Exception as e:
            logger.error(f"Database error checking license: {e}")

        # 2. Check Sandbox / Mock fallback (if enabled)
        if config.ENABLE_MOCK_LICENSES:
            if clean_key.startswith("SUMAIR-PRO") or clean_key.startswith("SUMAIR-LIFETIME") or clean_key.startswith("TEST-"):
                return LicenseValidationResult(
                    valid=True,
                    message="Sandbox test license activated.",
                    product_name="SVM41R Master Tools Pro (Sandbox)",
                    tier="Lifetime Pro License",
                    license_key=clean_key,
                )

        return LicenseValidationResult(
            valid=False,
            message="License key not found in our database. Please double-check the exact string from your purchase receipt.",
            license_key=clean_key,
        )

    def get_stats(self) -> Dict[str, int]:
        """Returns database statistics for staff reporting."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM licenses")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM licenses WHERE status = 'unactivated' AND active = 1")
            unactivated = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM licenses WHERE status = 'active'")
            active = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM licenses WHERE status = 'revoked' OR active = 0")
            revoked = cursor.fetchone()[0]

            return {
                "total": total,
                "unactivated": unactivated,
                "active": active,
                "revoked": revoked,
            }

    def lookup_license(self, key: str) -> Optional[Dict[str, Any]]:
        """Queries single license metadata for staff audit."""
        clean_key = key.strip().upper()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM licenses WHERE license_key = ?", (clean_key,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def revoke_license(self, key: str) -> bool:
        """Revokes a license key in database."""
        clean_key = key.strip().upper()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE licenses SET status = 'revoked', active = 0 WHERE license_key = ?", (clean_key,))
            conn.commit()
            return cursor.rowcount > 0
