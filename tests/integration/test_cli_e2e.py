import json
import os
import subprocess
import sys
from pathlib import Path

from tests.helpers import sample_graph_payload


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
            "get-learning-prompt",
            "--plan-id",
            plan_id,
            "--topic-id",
            "t1",
        ]
    )
    assert "Socratic learning coach" in learn_prompt["prompt_text"]

    commit = _run_cli(
        [
            "append-learning-record",
            "--plan-id",
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
    assert commit["state_delta_summary"]["mastery_level"] in {
        "Learning",
        "Proficient",
        "Mastered",
    }


def test_cli_api_discovery_commands(isolated_db):
    listed = _run_cli(["list-apis"])
    names = {api["name"] for api in listed}
    assert "get_learning_prompt" in names
    assert "ingest_knowledge_graph" in names

    spec = _run_cli(["get-api-spec", "--api-name", "append_learning_record"])
    assert spec["name"] == "append_learning_record"
    assert "required" in spec["input_schema"]
