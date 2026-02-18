from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sys

APP_NAME = "SlideApp"
SOURCE_ROOT = Path(__file__).resolve().parents[1]
PBKDF2_ROUNDS = 120_000


def _default_data_dir() -> Path:
    env_dir = os.environ.get("SLIDEAPP_DATA_DIR", "").strip()
    if env_dir:
        return Path(env_dir).expanduser()

    # macOS default for distributable app data.
    if os.name == "posix" and "darwin" in os.uname().sysname.lower():
        return Path.home() / "Library" / "Application Support" / APP_NAME

    # Generic fallback for non-mac platforms.
    return Path.home() / ".local" / "share" / APP_NAME


DATA_DIR = _default_data_dir()
DB_PATH = DATA_DIR / "slideapp.db"
EXPORTS_DIR = DATA_DIR / "exports"

LEGACY_DB_PATH = SOURCE_ROOT / "db" / "slideapp.db"
LEGACY_EXPORTS_DIR = SOURCE_ROOT / "exports"


def _migrate_legacy_data_if_needed() -> None:
    if DB_PATH.exists():
        return

    if LEGACY_DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LEGACY_DB_PATH, DB_PATH)

    if LEGACY_EXPORTS_DIR.exists():
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        for src in LEGACY_EXPORTS_DIR.glob("*.json"):
            dst = EXPORTS_DIR / src.name
            if not dst.exists():
                shutil.copy2(src, dst)


def _likely_external_exports_dir() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    exe = Path(sys.executable).resolve()
    # .../<project>/dist/SlideAppBeta.app/Contents/MacOS/SlideAppBeta
    # Want .../<project>/exports
    try:
        project_root = exe.parent.parent.parent.parent.parent
    except IndexError:
        return None
    candidate = project_root / "exports"
    return candidate if candidate.exists() else None


def _import_export_jsons_into_runs_if_empty(conn: sqlite3.Connection) -> None:
    run_count = conn.execute("SELECT COUNT(*) FROM experiment_runs").fetchone()[0]
    if int(run_count) > 0:
        return

    export_dirs: list[Path] = [EXPORTS_DIR, LEGACY_EXPORTS_DIR]
    external = _likely_external_exports_dir()
    if external is not None:
        export_dirs.append(external)

    seen_content: set[str] = set()
    for export_dir in export_dirs:
        if not export_dir.exists():
            continue
        for src in sorted(export_dir.glob("*.json")):
            try:
                payload_text = src.read_text(encoding="utf-8")
                payload = json.loads(payload_text)
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue

            username = str(payload.get("username", "")).strip() or "unknown_user"
            if username == "unknown_user":
                continue

            # Ensure FK user exists for imported historical exports.
            user_row = conn.execute(
                "SELECT username FROM app_users WHERE username = ?",
                (username,),
            ).fetchone()
            if user_row is None:
                salt_hex = secrets.token_hex(16)
                password_hash = _hash_password("temporary", salt_hex)
                conn.execute(
                    """
                    INSERT INTO app_users (username, role, password_salt, password_hash)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, "researcher", salt_hex, password_hash),
                )

            # Prevent duplicate inserts when scanning multiple directories.
            content_key = payload_text.strip()
            if content_key in seen_content:
                continue
            seen_content.add(content_key)

            created_at = datetime.now(timezone.utc).isoformat()
            stem = src.stem
            parts = stem.split("_")
            run_id = parts[-1] if parts else uuid.uuid4().hex[:8]
            if not run_id:
                run_id = uuid.uuid4().hex[:8]
            run_id = run_id.replace("-", "")
            if len(run_id) < 8:
                run_id = f"{run_id}{uuid.uuid4().hex[:8-len(run_id)]}"

            # Ensure unique key.
            exists = conn.execute(
                "SELECT run_id FROM experiment_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if exists is not None:
                run_id = uuid.uuid4().hex

            conn.execute(
                """
                INSERT INTO experiment_runs (run_id, username, created_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, username, created_at, payload_text),
            )


def _hash_password(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return digest.hex()


def init_auth_db() -> None:
    _migrate_legacy_data_if_needed()
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

        _import_export_jsons_into_runs_if_empty(conn)
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
