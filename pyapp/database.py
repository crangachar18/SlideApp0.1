from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[1] / "db" / "slideapp.db"
PBKDF2_ROUNDS = 120_000
EXPORTS_DIR = Path(__file__).resolve().parents[1] / "exports"


def _hash_password(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return digest.hex()


def init_auth_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_users (
              username TEXT PRIMARY KEY,
              role TEXT NOT NULL CHECK (role IN ('admin', 'researcher')),
              password_salt TEXT NOT NULL,
              password_hash TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS experiment_runs (
              run_id TEXT PRIMARY KEY,
              username TEXT NOT NULL,
              created_at TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              FOREIGN KEY (username) REFERENCES app_users(username) ON DELETE RESTRICT
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_storage_locations (
              username TEXT NOT NULL,
              location TEXT NOT NULL,
              last_used_at TEXT NOT NULL,
              PRIMARY KEY (username, location),
              FOREIGN KEY (username) REFERENCES app_users(username) ON DELETE CASCADE
            )
            """
        )

        row = conn.execute(
            "SELECT username FROM app_users WHERE username = ?", ("chetan",)
        ).fetchone()

        if row is None:
            salt_hex = secrets.token_hex(16)
            password_hash = _hash_password("trial", salt_hex)
            conn.execute(
                """
                INSERT INTO app_users (username, role, password_salt, password_hash)
                VALUES (?, ?, ?, ?)
                """,
                ("chetan", "admin", salt_hex, password_hash),
            )

        conn.commit()


def verify_credentials(username: str, password: str) -> str | None:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT role, password_salt, password_hash
            FROM app_users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    if row is None:
        return None

    role, salt_hex, expected_hash = row
    provided_hash = _hash_password(password, salt_hex)
    if secrets.compare_digest(provided_hash, expected_hash):
        return role

    return None


def get_user_storage_locations(username: str) -> list[str]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT location
            FROM user_storage_locations
            WHERE username = ?
            ORDER BY last_used_at DESC
            """,
            (username,),
        ).fetchall()
    return [row[0] for row in rows]


def remember_user_storage_location(username: str, location: str) -> None:
    loc = location.strip()
    if not loc:
        return
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO user_storage_locations (username, location, last_used_at)
            VALUES (?, ?, ?)
            ON CONFLICT(username, location) DO UPDATE SET last_used_at = excluded.last_used_at
            """,
            (username, loc, now),
        )
        conn.commit()


def save_experiment_payload(username: str, payload: dict[str, Any]) -> tuple[str, Path]:
    run_id = uuid.uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()
    payload_json = json.dumps(payload, indent=2, sort_keys=True)

    out_file = EXPORTS_DIR / f"{created_at[:10]}_{username}_{run_id[:8]}.json"
    out_file.write_text(payload_json, encoding="utf-8")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO experiment_runs (run_id, username, created_at, payload_json)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, username, created_at, payload_json),
        )
        conn.commit()

    return run_id, out_file


def list_experiment_runs(username: str) -> list[dict[str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT run_id, created_at, payload_json
            FROM experiment_runs
            WHERE username = ?
            ORDER BY created_at DESC
            """,
            (username,),
        ).fetchall()

    out: list[dict[str, str]] = []
    for run_id, created_at, payload_json in rows:
        out.append(
            {
                "run_id": run_id,
                "created_at": created_at,
                "payload_json": payload_json,
            }
        )
    return out
