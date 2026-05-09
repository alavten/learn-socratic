import json
import os
import subprocess
import sys
from pathlib import Path

from tests.fixtures.software_engineering_payloads import build_software_engineering_payload


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_cli(args: list[str]) -> dict | list:
    root = _project_root()
    result = subprocess.run(
        [sys.executable, "-m", "scripts.cli.main", *args],
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


def test_real_flow_with_software_engineering_materials(isolated_db, tmp_path):
    chapter_dir = _project_root() / "tests" / "assert" / "SoftwareEngineering"
    payload = build_software_engineering_payload(chapter_dir)
    payload_file = tmp_path / "software_engineering_payload.json"
    payload_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    ingest = _run_cli(
        [
            "ingest-knowledge-graph",
            "--graph-id",
            "se-real",
            "--payload-file",
            str(payload_file),
        ]
    )
    assert ingest["validation_summary"]["ok"] is True
    assert ingest["validation_summary"]["stats"]["concept_count"] >= 20
    assert ingest["validation_summary"]["stats"]["relation_count"] >= 19

    graph_detail = _run_cli(["get-knowledge-graph", "--graph-id", "se-real", "--concept-limit", "30"])
    assert len(graph_detail["topics"]) >= 20
    assert len(graph_detail["concept_briefs"]) >= 20

    created = _run_cli(["create-learning-plan", "--graph-id", "se-real"])
    plan_id = created["plan_id"]

    learn_prompt = _run_cli(["get-mode-context", "--mode", "learn", "--plan-id", plan_id])
    prompt_text = learn_prompt["prompt_text"]
    assert "Feynman loop" in prompt_text
    assert "Explain, Interpret, Apply" in prompt_text

    first_concept = payload["concepts"][0]["concept_id"]
    learn_commit = _run_cli(
        [
            "add-interaction-record",
            "--context-id",
            plan_id,
            "--mode",
            "learn",
            "--concept-id",
            first_concept,
            "--result",
            "ok",
            "--score",
            "80",
            "--difficulty-bucket",
            "medium",
        ]
    )
    assert learn_commit["commit_result"]["record_type"] == "learn"

    quiz_prompt = _run_cli(["get-mode-context", "--mode", "quiz", "--plan-id", plan_id])
    quiz_text = quiz_prompt["prompt_text"]
    assert "SOLO levels" in quiz_text
    assert "retrieval-first" in quiz_text

    second_concept = payload["concepts"][1]["concept_id"]
    quiz_commit = _run_cli(
        [
            "add-interaction-record",
            "--context-id",
            plan_id,
            "--mode",
            "quiz",
            "--concept-id",
            second_concept,
            "--result",
            "correct",
            "--score",
            "88",
            "--difficulty-bucket",
            "hard",
        ]
    )
    assert quiz_commit["commit_result"]["record_type"] == "quiz"

    review_prompt = _run_cli(["get-mode-context", "--mode", "review", "--plan-id", plan_id])
    review_text = review_prompt["prompt_text"]
    assert "spacing-first order" in review_text
    assert review_prompt["context_summary"]["candidate_items"]

    review_commit = _run_cli(
        [
            "add-interaction-record",
            "--context-id",
            plan_id,
            "--mode",
            "review",
            "--concept-id",
            first_concept,
            "--result",
            "correct",
            "--score",
            "92",
            "--difficulty-bucket",
            "easy",
        ]
    )
    assert review_commit["commit_result"]["record_type"] == "review"
