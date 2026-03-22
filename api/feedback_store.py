"""
SQLite-backed feedback capture for the sharable alpha build.
"""

from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone


def get_feedback_db_path() -> str:
    path = os.environ.get("ERSIM_FEEDBACK_DB", "/tmp/ersim_feedback.db")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def get_build_version() -> str:
    return os.environ.get("ERSIM_BUILD_VERSION", "alpha-local")


def init_feedback_db() -> None:
    path = get_feedback_db_path()
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                session_id TEXT NOT NULL,
                build_version TEXT NOT NULL,
                shift_mode TEXT NOT NULL,
                debrief_grade TEXT NOT NULL,
                tester_role TEXT NOT NULL,
                overall_rating INTEGER NOT NULL,
                best_moment TEXT NOT NULL,
                most_confusing_part TEXT NOT NULL,
                would_you_use_again INTEGER NOT NULL,
                optional_contact TEXT NOT NULL,
                disposition_accuracy REAL,
                resolved_cases INTEGER,
                total_cases INTEGER,
                clinical_depth REAL,
                trap_cases_fully_caught INTEGER,
                trap_cases_partially_recovered INTEGER,
                autonomous_actions INTEGER,
                warnings_heeded INTEGER,
                attention_distribution TEXT,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_feedback(payload: dict) -> int:
    metrics = payload.get("metrics", {}) or {}
    created_at = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
    with closing(sqlite3.connect(get_feedback_db_path())) as conn:
        cur = conn.execute(
            """
            INSERT INTO feedback (
                created_at, session_id, build_version, shift_mode, debrief_grade,
                tester_role, overall_rating, best_moment, most_confusing_part,
                would_you_use_again, optional_contact,
                disposition_accuracy, resolved_cases, total_cases, clinical_depth,
                trap_cases_fully_caught, trap_cases_partially_recovered,
                autonomous_actions, warnings_heeded, attention_distribution,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                payload["session_id"],
                payload["build_version"],
                payload["shift_mode"],
                payload["debrief_grade"],
                payload["tester_role"],
                payload["overall_rating"],
                payload["best_moment"],
                payload["most_confusing_part"],
                1 if payload["would_you_use_again"] else 0,
                payload.get("optional_contact", ""),
                metrics.get("disposition_accuracy"),
                metrics.get("resolved_cases"),
                metrics.get("total_cases"),
                metrics.get("clinical_depth"),
                metrics.get("trap_cases_fully_caught"),
                metrics.get("trap_cases_partially_recovered"),
                metrics.get("autonomous_actions"),
                metrics.get("warnings_heeded"),
                metrics.get("attention_distribution"),
                json.dumps(payload, ensure_ascii=True),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def export_feedback_csv() -> str:
    with closing(sqlite3.connect(get_feedback_db_path())) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                created_at, session_id, build_version, shift_mode, debrief_grade,
                tester_role, overall_rating, best_moment, most_confusing_part,
                would_you_use_again, optional_contact,
                disposition_accuracy, resolved_cases, total_cases, clinical_depth,
                trap_cases_fully_caught, trap_cases_partially_recovered,
                autonomous_actions, warnings_heeded, attention_distribution
            FROM feedback
            ORDER BY id DESC
            """
        ).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "created_at",
        "session_id",
        "build_version",
        "shift_mode",
        "debrief_grade",
        "tester_role",
        "overall_rating",
        "best_moment",
        "most_confusing_part",
        "would_you_use_again",
        "optional_contact",
        "disposition_accuracy",
        "resolved_cases",
        "total_cases",
        "clinical_depth",
        "trap_cases_fully_caught",
        "trap_cases_partially_recovered",
        "autonomous_actions",
        "warnings_heeded",
        "attention_distribution",
    ])
    for row in rows:
        writer.writerow([row[key] for key in row.keys()])
    return buf.getvalue()
