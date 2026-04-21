import sqlite3

from scripts.foundation.storage import query_one, transaction


def test_transaction_rolls_back_on_error(isolated_db):
    try:
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO Learner(learnerId, profileId, timezone, locale, status, createdAt, updatedAt)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("rollback-user", "p", "UTC", "zh-CN", "active", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
            )
            # Duplicate PK forces rollback for the entire transaction.
            conn.execute(
                """
                INSERT INTO Learner(learnerId, profileId, timezone, locale, status, createdAt, updatedAt)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("rollback-user", "p2", "UTC", "zh-CN", "active", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
            )
    except sqlite3.IntegrityError:
        pass

    row = query_one(
        "SELECT learnerId AS learner_id FROM Learner WHERE learnerId = ?",
        ("rollback-user",),
    )
    assert row is None
