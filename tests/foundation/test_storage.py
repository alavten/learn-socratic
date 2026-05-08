import pytest

from scripts.foundation.storage import execute, paginate, query_one


@pytest.mark.parametrize(
    ("limit", "offset", "expected"),
    [
        (20, None, (20, 0)),
        (0, None, (1, 0)),
        (-10, "-5", (1, 0)),
        (999, "2", (200, 2)),
    ],
)
def test_paginate_bounds(limit, offset, expected):
    assert paginate(limit, offset) == expected


def test_paginate_invalid_offset_raises_value_error():
    with pytest.raises(ValueError):
        paginate(10, "not-a-number")


def test_execute_and_query_roundtrip_on_existing_tables(isolated_db):
    rows = execute(
        """
        INSERT INTO Learner(learnerId, profileId, timezone, locale, status, createdAt, updatedAt)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("l1", "p1", "UTC", "zh-CN", "active", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
    )
    assert rows == 1

    row = query_one(
        "SELECT learnerId AS learner_id, profileId AS profile_id FROM Learner WHERE learnerId = ?",
        ("l1",),
    )
    assert row == {"learner_id": "l1", "profile_id": "p1"}
