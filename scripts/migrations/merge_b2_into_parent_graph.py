"""Merge b2-ch* child graphs into claude-harness-vs-codex-harness (single graph + Topic tree).

Preserves all Concept and LearningPlan rows (no DELETE on those tables).
Resolves uq_concept_current duplicate by setting one AGENTS row to dr=1 before co-locating graphIds.

Usage:
  python scripts/migrations/merge_b2_into_parent_graph.py --db-path data/skill.sqlite3 --dry-run
  python scripts/migrations/merge_b2_into_parent_graph.py --db-path data/skill.sqlite3
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TARGET_GRAPH_ID = "claude-harness-vs-codex-harness"

CHILD_GRAPH_IDS: tuple[str, ...] = (
    "b2-ch00-reading-map",
    "b2-ch01-why-this-comparison",
    "b2-ch02-two-control-planes",
    "b2-ch03-loop-thread-rollout",
    "b2-ch04-tools-sandbox-exec-policy",
    "b2-ch05-skills-hooks-local-governance",
    "b2-ch06-delegation-verification-state",
    "b2-ch07-convergence-divergence",
    "b2-ch08-how-to-choose-or-build",
)

# Canonical duplicate pair (ch02 keeps dr=0 per plan: smaller chapter wins)
ARCHIVE_CONCEPT_ID = "b2-ch05-agents-md-hierarchy"

ROOT_CHAPTER_IDS_ORDER: tuple[tuple[str, int], ...] = (
    ("b2-ch00", 1),
    ("b2-ch01", 2),
    ("b2-ch02", 3),
    ("b2-ch03", 4),
    ("b2-ch04", 5),
    ("b2-ch05", 6),
    ("b2-ch06", 7),
    ("b2-ch07", 8),
    ("b2-ch08", 9),
)


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _precheck(conn: sqlite3.Connection) -> dict[str, Any]:
    cur = conn.cursor()
    missing = [
        gid
        for gid in (TARGET_GRAPH_ID, *CHILD_GRAPH_IDS)
        if cur.execute("SELECT 1 FROM Graph WHERE graphId = ?", (gid,)).fetchone() is None
    ]
    stats: dict[str, Any] = {"missing_graphs": missing}
    for gid in CHILD_GRAPH_IDS:
        stats[f"topics_{gid}"] = cur.execute(
            "SELECT COUNT(*) FROM Topic WHERE graphId = ?", (gid,)
        ).fetchone()[0]
        stats[f"concepts_{gid}"] = cur.execute(
            "SELECT COUNT(*) FROM Concept WHERE graphId = ? AND dr = 0", (gid,)
        ).fetchone()[0]
    stats["duplicate_canonical_pairs"] = cur.execute(
        """
        SELECT canonicalName, language, conceptType, COUNT(*) AS n
        FROM Concept
        WHERE graphId IN ({ph}) AND dr = 0
        GROUP BY canonicalName, language, conceptType
        HAVING n > 1
        """.format(ph=",".join("?" * len(CHILD_GRAPH_IDS))),
        CHILD_GRAPH_IDS,
    ).fetchall()
    return stats


def run_merge(conn: sqlite3.Connection, *, dry_run: bool) -> dict[str, Any]:
    stats = _precheck(conn)
    if dry_run:
        return {"dry_run": True, "precheck": stats}

    if stats["missing_graphs"]:
        raise SystemExit(f"precheck failed: missing graphs: {stats['missing_graphs']}")

    now = datetime.now(timezone.utc).isoformat()
    ph = ",".join("?" * len(CHILD_GRAPH_IDS))
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE Concept SET dr = 1, drtime = ?, updatedAt = ?
        WHERE conceptId = ? AND dr = 0
        """,
        (now, now, ARCHIVE_CONCEPT_ID),
    )
    if cur.rowcount != 1:
        raise SystemExit(f"expected exactly 1 archived concept row, got {cur.rowcount}")

    cur.execute(
        f"UPDATE Concept SET graphId = ? WHERE graphId IN ({ph})",
        (TARGET_GRAPH_ID, *CHILD_GRAPH_IDS),
    )
    concepts_moved = cur.rowcount

    cur.execute(
        f"UPDATE ConceptRelation SET graphId = ? WHERE graphId IN ({ph})",
        (TARGET_GRAPH_ID, *CHILD_GRAPH_IDS),
    )
    relations_moved = cur.rowcount

    cur.execute(
        f"UPDATE Topic SET graphId = ? WHERE graphId IN ({ph})",
        (TARGET_GRAPH_ID, *CHILD_GRAPH_IDS),
    )
    topics_moved = cur.rowcount

    for topic_id, sort_order in ROOT_CHAPTER_IDS_ORDER:
        cur.execute(
            """
            UPDATE Topic SET sortOrder = ?
            WHERE topicId = ? AND graphId = ? AND parentTopicId IS NULL AND topicType = 'chapter'
            """,
            (sort_order, topic_id, TARGET_GRAPH_ID),
        )
        if cur.rowcount != 1:
            raise SystemExit(f"root chapter sort update failed for {topic_id}: rowcount={cur.rowcount}")

    cur.execute(
        f"""
        UPDATE LearningPlan SET graphId = ?, updatedAt = ?
        WHERE graphId IN ({ph})
        """,
        (TARGET_GRAPH_ID, now, *CHILD_GRAPH_IDS),
    )
    plans_updated = cur.rowcount

    cur.execute(
        f"DELETE FROM Graph WHERE graphId IN ({ph})",
        CHILD_GRAPH_IDS,
    )
    graphs_deleted = cur.rowcount
    if graphs_deleted != len(CHILD_GRAPH_IDS):
        raise SystemExit(f"expected {len(CHILD_GRAPH_IDS)} graphs deleted, got {graphs_deleted}")

    return {
        "dry_run": False,
        "precheck": stats,
        "concepts_moved": concepts_moved,
        "relations_moved": relations_moved,
        "topics_moved": topics_moved,
        "plans_updated": plans_updated,
        "graphs_deleted": graphs_deleted,
        "archived_concept_id": ARCHIVE_CONCEPT_ID,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db-path",
        type=Path,
        required=True,
        help="Path to skill.sqlite3 (use absolute path outside repo if needed)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Run precheck only, no writes")
    args = parser.parse_args()
    db_path = args.db_path.expanduser().resolve()
    if not db_path.is_file():
        raise SystemExit(f"database file not found: {db_path}")

    conn = _connect(db_path)
    try:
        if args.dry_run:
            out = run_merge(conn, dry_run=True)
            print(out)
            return
        out = run_merge(conn, dry_run=False)
        conn.commit()
        print(out)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
