import json
import os
import subprocess
import sys
from pathlib import Path

from tests.helpers import sample_graph_payload


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _learning_payload_error_from_stderr(stderr: str) -> dict:
    for line in reversed(stderr.strip().splitlines()):
        raw = line.strip()
        if raw.startswith("{") and '"error_code"' in raw:
            return json.loads(raw)
    raise AssertionError(f"No LearningPayloadError JSON in stderr: {stderr!r}")


def _run_cli_expect_failure(args: list[str]) -> subprocess.CompletedProcess[str]:
    root = _project_root()
    return subprocess.run(
        [sys.executable, "-m", "scripts.cli.main", *args],
        cwd=root,
        env=os.environ.copy(),
        check=False,
        capture_output=True,
        text=True,
    )


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

    # CLI also logs bootstrap info; parse JSON from the first object/array token.
    start_candidates = [idx for idx in [stdout.find("{"), stdout.find("[")] if idx != -1]
    assert start_candidates, f"No JSON found in CLI output: {stdout}"
    start = min(start_candidates)
    return json.loads(stdout[start:])


def test_cli_end_to_end_ingest_plan_prompt_record(isolated_db, tmp_path):
    payload = sample_graph_payload()
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(json.dumps(payload), encoding="utf-8")

    ingest = _run_cli(
        [
            "ingest-knowledge-graph",
            "--graph-id",
            "g-cli",
            "--payload-file",
            str(payload_file),
        ]
    )
    assert ingest["validation_summary"]["ok"] is True
    assert ingest["version"] == 1

    plans_before = _run_cli(["list-learning-plans"])
    assert plans_before["items"] == []

    created = _run_cli(
        [
            "create-learning-plan",
            "--graph-id",
            "g-cli",
            "--topic-id",
            "t1",
        ]
    )
    plan_id = created["plan_id"]

    learn_prompt = _run_cli(
        [
            "get-mode-context",
            "--mode",
            "learn",
            "--plan-id",
            plan_id,
            "--topic-id",
            "t1",
        ]
    )
    assert "Socratic learning coach" in learn_prompt["prompt_text"]

    commit = _run_cli(
        [
            "add-interaction-record",
            "--context-id",
            plan_id,
            "--mode",
            "learn",
            "--concept-id",
            "c1",
            "--result",
            "ok",
            "--score",
            "82",
            "--difficulty-bucket",
            "easy",
            "--latency-ms",
            "450",
        ]
    )
    assert commit["commit_result"]["record_type"] == "learn"
    assert commit["plan_delta_summary"]["plan_id"] == plan_id
    assert commit["plan_delta_summary"]["plan_touched"] is True
    assert commit["state_delta_summary"]["mastery_level"] in {
        "Learning",
        "Proficient",
        "Mastered",
    }

    commit_c2 = _run_cli(
        [
            "add-interaction-record",
            "--context-id",
            plan_id,
            "--mode",
            "quiz",
            "--concept-id",
            "c2",
            "--result",
            "incorrect",
            "--score",
            "35",
            "--difficulty-bucket",
            "hard",
        ]
    )
    assert commit_c2["commit_result"]["concept_id"] == "c2"

    review_prompt = _run_cli(
        [
            "get-mode-context",
            "--mode",
            "review",
            "--plan-id",
            plan_id,
            "--session-context-json",
            '{"served_concept_ids":["c1"],"last_result":"correct","last_completed_concept_id":"c1"}',
        ]
    )
    summary = review_prompt["context_summary"]
    assert "session_queue" in summary
    assert "next_session_context" in summary
    current = summary["session_queue"]["current_item"]
    if current:
        assert current["concept_id"] != "c1"


def test_cli_add_interaction_record_unknown_concept_stderr_json(isolated_db, tmp_path):
    payload = sample_graph_payload()
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(json.dumps(payload), encoding="utf-8")

    _run_cli(["ingest-knowledge-graph", "--graph-id", "g-cli-err", "--payload-file", str(payload_file)])
    created = _run_cli(["create-learning-plan", "--graph-id", "g-cli-err", "--topic-id", "t1"])
    plan_id = created["plan_id"]

    proc = _run_cli_expect_failure(
        [
            "add-interaction-record",
            "--context-id",
            plan_id,
            "--mode",
            "learn",
            "--concept-id",
            "unknown-concept",
            "--result",
            "ok",
        ]
    )
    assert proc.returncode == 1
    err_obj = _learning_payload_error_from_stderr(proc.stderr)
    assert err_obj["error_code"] == "concept_not_in_plan_graph"
    assert "unknown-concept" in err_obj["message"]


def test_cli_api_discovery_commands(isolated_db):
    listed = _run_cli(["list-apis"])
    names = {api["name"] for api in listed}
    assert "get_learn_context" in names
    assert "ingest_knowledge_graph" in names
    assert "remove_knowledge_graph_entities" in names

    spec = _run_cli(["get-api-spec", "--api-name", "add_interaction_record"])
    assert spec["name"] == "add_interaction_record"
    assert "required" in spec["input_schema"]
