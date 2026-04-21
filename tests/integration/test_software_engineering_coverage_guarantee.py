import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.foundation.storage import query_all
from tests.fixtures.software_engineering_payloads import build_software_engineering_payload


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_cli(args: list[str]) -> dict | list:
    root = _project_root()
    result = subprocess.run(
        [sys.executable, "scripts/cli.py", *args],
        cwd=root,
        env=os.environ.copy(),
        check=True,
        capture_output=True,
        text=True,
    )
    stdout = result.stdout.strip()
    start_candidates = [idx for idx in [stdout.find("{"), stdout.find("[")] if idx != -1]
    assert start_candidates, f"No JSON found in CLI output: {stdout}"
    start = min(start_candidates)
    return json.loads(stdout[start:])


def test_software_engineering_full_path_coverage_and_methodology(isolated_db, tmp_path):
    chapter_dir = _project_root() / "tests" / "assert" / "SoftwareEngineering"
    payload = build_software_engineering_payload(chapter_dir)
    payload_file = tmp_path / "se_coverage_payload.json"
    payload_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    ingest = _run_cli(
        [
            "ingest-knowledge-graph",
            "--graph-id",
            "se-coverage",
            "--payload-file",
            str(payload_file),
        ]
    )
    assert ingest["validation_summary"]["ok"] is True

    created = _run_cli(["create-learning-plan", "--graph-id", "se-coverage"])
    plan_id = created["plan_id"]

    learn_prompt = _run_cli(["get-learning-prompt", "--plan-id", plan_id])["prompt_text"]
    quiz_prompt = _run_cli(["get-quiz-prompt", "--plan-id", plan_id])["prompt_text"]
    review_prompt = _run_cli(["get-review-prompt", "--plan-id", plan_id])["prompt_text"]
    assert "Feynman loop" in learn_prompt
    assert "Explain, Interpret, Apply" in learn_prompt
    assert "SOLO levels" in quiz_prompt
    assert "UBD facet" in quiz_prompt
    assert "spacing-first order" in review_prompt
    assert "retrieval-first" in review_prompt

    concept_ids = [item["concept_id"] for item in payload["concepts"]]
    practiced_ids: set[str] = set()
    modes = ["learn", "quiz", "review"]
    scores = {"learn": "78", "quiz": "84", "review": "90"}
    results = {"learn": "ok", "quiz": "correct", "review": "correct"}
    buckets = {"learn": "medium", "quiz": "hard", "review": "easy"}
    for idx, concept_id in enumerate(concept_ids):
        mode = modes[idx % len(modes)]
        _run_cli(
            [
                "append-learning-record",
                "--plan-id",
                plan_id,
                "--mode",
                mode,
                "--concept-id",
                concept_id,
                "--result",
                results[mode],
                "--score",
                scores[mode],
                "--difficulty-bucket",
                buckets[mode],
            ]
        )
        practiced_ids.add(concept_id)

    state_rows = query_all(
        """
        SELECT conceptId AS concept_id
        FROM LearnerConceptState
        WHERE learningPlanId = ?
        """,
        (plan_id,),
    )
    persisted_covered = {row["concept_id"] for row in state_rows}
    total = len(concept_ids)
    coverage = len(persisted_covered) / total if total else 0.0

    assert practiced_ids == persisted_covered
    assert total >= 20
    assert coverage >= 0.95

    record_types = query_all(
        """
        SELECT recordType AS record_type, COUNT(*) AS count
        FROM LearningRecord lr
        JOIN LearningSession ls ON ls.sessionId = lr.sessionId
        WHERE ls.learningPlanId = ?
        GROUP BY recordType
        """,
        (plan_id,),
    )
    type_counts = {row["record_type"]: row["count"] for row in record_types}
    assert type_counts.get("learn", 0) > 0
    assert type_counts.get("quiz", 0) > 0
    assert type_counts.get("review", 0) > 0
