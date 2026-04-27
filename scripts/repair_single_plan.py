"""Repair utility: enforce a single learning plan per graph.

This script keeps a designated main plan for a graph, merges missing topic scope
from duplicate plans into the main plan, merges runtime learning data into the
main plan with "main plan first, duplicates fill gaps" policy, and removes
redundant plans.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _get_plan_ids(conn: sqlite3.Connection, graph_id: str) -> list[str]:
    rows = conn.execute(
        """
        SELECT learningPlanId
        FROM LearningPlan
        WHERE graphId = ?
        ORDER BY updatedAt DESC, createdAt DESC
        """,
        (graph_id,),
    ).fetchall()
    return [str(row["learningPlanId"]) for row in rows]


def _collect_preview(conn: sqlite3.Connection, graph_id: str, main_plan_id: str) -> dict[str, Any]:
    all_plan_ids = _get_plan_ids(conn, graph_id)
    duplicate_plan_ids = [pid for pid in all_plan_ids if pid != main_plan_id]

    if main_plan_id not in all_plan_ids:
        raise ValueError(f"main_plan_not_found_for_graph: {main_plan_id}")

    main_topics = {
        str(row["topicId"])
        for row in conn.execute(
            "SELECT topicId FROM LearningPlanTopic WHERE learningPlanId = ?",
            (main_plan_id,),
        ).fetchall()
    }

    duplicate_topics = {
        str(row["topicId"])
        for row in conn.execute(
            """
            SELECT DISTINCT topicId
            FROM LearningPlanTopic
            WHERE learningPlanId IN (
                SELECT learningPlanId FROM LearningPlan WHERE graphId = ? AND learningPlanId != ?
            )
            """,
            (graph_id, main_plan_id),
        ).fetchall()
    }
    topics_to_merge = sorted(duplicate_topics - main_topics)

    def _count(table: str, ref_column: str = "learningPlanId") -> int:
        if not duplicate_plan_ids:
            return 0
        placeholders = ",".join("?" for _ in duplicate_plan_ids)
        sql = f"SELECT COUNT(*) AS c FROM {table} WHERE {ref_column} IN ({placeholders})"
        row = conn.execute(sql, tuple(duplicate_plan_ids)).fetchone()
        return int(row["c"] if row else 0)

    duplicate_record_count = 0
    if duplicate_plan_ids:
        placeholders = ",".join("?" for _ in duplicate_plan_ids)
        duplicate_record_count = int(
            conn.execute(
                f"""
                SELECT COUNT(*) AS c
                FROM LearningRecord lr
                JOIN LearningSession ls ON ls.sessionId = lr.sessionId
                WHERE ls.learningPlanId IN ({placeholders})
                """,
                tuple(duplicate_plan_ids),
            ).fetchone()["c"]
        )

    main_record_count = int(
        conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM LearningRecord lr
            JOIN LearningSession ls ON ls.sessionId = lr.sessionId
            WHERE ls.learningPlanId = ?
            """,
            (main_plan_id,),
        ).fetchone()["c"]
    )

    return {
        "graph_id": graph_id,
        "main_plan_id": main_plan_id,
        "all_plan_ids": all_plan_ids,
        "duplicate_plan_ids": duplicate_plan_ids,
        "duplicate_plan_count": len(duplicate_plan_ids),
        "topics_to_merge": topics_to_merge,
        "counts_to_delete": {
            "learning_plan_topics": _count("LearningPlanTopic"),
            "learning_tasks": _count("LearningTask"),
            "learning_sessions": _count("LearningSession"),
            "learner_concept_states": _count("LearnerConceptState"),
            "learning_records_via_sessions": duplicate_record_count,
            "learning_plans": len(duplicate_plan_ids),
        },
        "main_plan_record_count_before": main_record_count,
    }


def _merge_runtime_data(conn: sqlite3.Connection, main_plan_id: str, duplicate_plan_ids: list[str]) -> dict[str, int]:
    summary = {
        "sessions_moved": 0,
        "records_moved_via_sessions": 0,
        "tasks_moved": 0,
        "tasks_dropped_as_duplicate": 0,
        "states_moved": 0,
        "states_dropped_as_duplicate": 0,
    }
    if not duplicate_plan_ids:
        return summary

    # 1) Move sessions to main plan (records follow sessions by FK).
    for plan_id in duplicate_plan_ids:
        session_rows = conn.execute(
            "SELECT sessionId FROM LearningSession WHERE learningPlanId = ?",
            (plan_id,),
        ).fetchall()
        if session_rows:
            summary["sessions_moved"] += len(session_rows)
            placeholders = ",".join("?" for _ in session_rows)
            session_ids = tuple(str(r["sessionId"]) for r in session_rows)
            moved_records = conn.execute(
                f"SELECT COUNT(*) AS c FROM LearningRecord WHERE sessionId IN ({placeholders})",
                session_ids,
            ).fetchone()
            summary["records_moved_via_sessions"] += int(moved_records["c"] if moved_records else 0)
            conn.execute(
                "UPDATE LearningSession SET learningPlanId = ? WHERE learningPlanId = ?",
                (main_plan_id, plan_id),
            )

    # 2) Merge tasks by (conceptId, status). Keep main-plan task if duplicate exists.
    for plan_id in duplicate_plan_ids:
        task_rows = conn.execute(
            """
            SELECT learningTaskId, conceptId, status
            FROM LearningTask
            WHERE learningPlanId = ?
            ORDER BY generatedAt DESC, createdAt DESC
            """,
            (plan_id,),
        ).fetchall()
        for row in task_rows:
            exists = conn.execute(
                """
                SELECT 1
                FROM LearningTask
                WHERE learningPlanId = ? AND conceptId = ? AND status = ?
                LIMIT 1
                """,
                (main_plan_id, row["conceptId"], row["status"]),
            ).fetchone()
            if exists:
                conn.execute("DELETE FROM LearningTask WHERE learningTaskId = ?", (row["learningTaskId"],))
                summary["tasks_dropped_as_duplicate"] += 1
            else:
                conn.execute(
                    "UPDATE LearningTask SET learningPlanId = ? WHERE learningTaskId = ?",
                    (main_plan_id, row["learningTaskId"]),
                )
                summary["tasks_moved"] += 1

    # 3) Merge concept states by (learnerId, conceptId). Keep main-plan state on conflict.
    main_learner = conn.execute(
        "SELECT learnerId FROM LearningPlan WHERE learningPlanId = ?",
        (main_plan_id,),
    ).fetchone()
    if not main_learner:
        raise ValueError(f"main_plan_not_found: {main_plan_id}")
    learner_id = str(main_learner["learnerId"])

    for plan_id in duplicate_plan_ids:
        state_rows = conn.execute(
            """
            SELECT learnerConceptStateId, conceptId
            FROM LearnerConceptState
            WHERE learningPlanId = ?
            """,
            (plan_id,),
        ).fetchall()
        for row in state_rows:
            exists = conn.execute(
                """
                SELECT 1
                FROM LearnerConceptState
                WHERE learnerId = ? AND learningPlanId = ? AND conceptId = ?
                LIMIT 1
                """,
                (learner_id, main_plan_id, row["conceptId"]),
            ).fetchone()
            if exists:
                conn.execute(
                    "DELETE FROM LearnerConceptState WHERE learnerConceptStateId = ?",
                    (row["learnerConceptStateId"],),
                )
                summary["states_dropped_as_duplicate"] += 1
            else:
                conn.execute(
                    "UPDATE LearnerConceptState SET learningPlanId = ? WHERE learnerConceptStateId = ?",
                    (main_plan_id, row["learnerConceptStateId"]),
                )
                summary["states_moved"] += 1

    return summary


def repair_single_plan(
    db_path: Path,
    graph_id: str,
    main_plan_id: str,
    apply_changes: bool,
) -> dict[str, Any]:
    with _connect(db_path) as conn:
        preview = _collect_preview(conn, graph_id, main_plan_id)
        if not apply_changes:
            preview["applied"] = False
            return preview

        now = _now()
        with conn:
            for topic_id in preview["topics_to_merge"]:
                exists = conn.execute(
                    "SELECT 1 FROM LearningPlanTopic WHERE learningPlanId = ? AND topicId = ?",
                    (main_plan_id, topic_id),
                ).fetchone()
                if exists:
                    continue
                conn.execute(
                    """
                    INSERT INTO LearningPlanTopic(learningPlanTopicId, learningPlanId, topicId, reason, createdAt)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), main_plan_id, topic_id, "dedupe_merge", now),
                )

            runtime_merge = _merge_runtime_data(conn, main_plan_id, preview["duplicate_plan_ids"])

            for plan_id in preview["duplicate_plan_ids"]:
                conn.execute("DELETE FROM LearningPlan WHERE learningPlanId = ?", (plan_id,))

            conn.execute(
                "UPDATE LearningPlan SET updatedAt = ? WHERE learningPlanId = ?",
                (now, main_plan_id),
            )

        postcheck = _collect_preview(conn, graph_id, main_plan_id)
        postcheck["applied"] = True
        postcheck["runtime_merge_summary"] = runtime_merge
        postcheck["main_plan_record_count_after"] = int(
            conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM LearningRecord lr
                JOIN LearningSession ls ON ls.sessionId = lr.sessionId
                WHERE ls.learningPlanId = ?
                """,
                (main_plan_id,),
            ).fetchone()["c"]
        )
        return postcheck


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair duplicate learning plans for one graph.")
    parser.add_argument(
        "--db-path",
        default=os.getenv("DOC_SOCRATIC_DB_PATH", "data/skill.sqlite3"),
        help="Path to SQLite DB (default: DOC_SOCRATIC_DB_PATH or data/skill.sqlite3)",
    )
    parser.add_argument("--graph-id", required=True)
    parser.add_argument("--main-plan-id", required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply repair. Without this flag the script only prints preview.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = repair_single_plan(
        db_path=Path(args.db_path),
        graph_id=args.graph_id,
        main_plan_id=args.main_plan_id,
        apply_changes=bool(args.apply),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
