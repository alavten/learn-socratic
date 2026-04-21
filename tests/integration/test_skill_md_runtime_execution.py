from pathlib import Path

from tests.fixtures.software_engineering_payloads import build_software_engineering_payload
from tests.skill_runtime_harness import SkillRuntime


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_skill_runtime_routes_and_executes_contracts_with_real_materials(isolated_db):
    runtime = SkillRuntime()
    chapter_dir = _project_root() / "tests" / "assert" / "SoftwareEngineering"
    payload = build_software_engineering_payload(chapter_dir)

    assert runtime.route_mode("请导入资料并建图") == "ingest"
    assert runtime.route_mode("我想学习这个主题") == "learn"
    assert runtime.route_mode("考考我") == "quiz"
    assert runtime.route_mode("开始复习") == "review"
    assert runtime.route_mode("继续", last_mode="quiz") == "quiz"
    assert runtime.route_mode("随便聊聊") == "shared"

    start = runtime.session_start("ingest")
    assert start["mode"] == "ingest"
    assert "next_step" in start and "summary" in start

    ingest = runtime.run_ingest(graph_id="se-runtime", payload=payload)
    assert ingest["mode"] == "ingest"
    assert ingest["status"] == "success"
    assert ingest["validation_summary"]["ok"] is True
    assert "summary" in ingest and "next_step" in ingest

    plan_id = runtime.ensure_plan(graph_id="se-runtime")

    learn = runtime.run_learn(plan_id=plan_id)
    assert learn["mode"] == "learn"
    assert "Feynman loop" in learn["content"]
    assert "summary" in learn and "next_step" in learn

    runtime.service.append_learning_record(
        plan_id,
        "learn",
        {"concept_id": payload["concepts"][0]["concept_id"], "result": "ok", "score": 82, "difficulty_bucket": "medium"},
    )

    quiz = runtime.run_quiz(plan_id=plan_id)
    assert quiz["mode"] == "quiz"
    assert "SOLO levels" in quiz["questions_or_feedback"]
    assert "UBD facet" in quiz["questions_or_feedback"]
    assert "summary" in quiz and "next_step" in quiz

    runtime.service.append_learning_record(
        plan_id,
        "quiz",
        {"concept_id": payload["concepts"][1]["concept_id"], "result": "correct", "score": 88, "difficulty_bucket": "hard"},
    )

    review = runtime.run_review(plan_id=plan_id)
    assert review["mode"] == "review"
    assert "spacing-first order" in review["review_items_or_feedback"]
    assert "summary" in review and "next_step" in review

    runtime.service.append_learning_record(
        plan_id,
        "review",
        {"concept_id": payload["concepts"][0]["concept_id"], "result": "correct", "score": 90, "difficulty_bucket": "easy"},
    )

    shared_ambiguous = runtime.run_shared("不太确定怎么开始")
    assert shared_ambiguous["mode"] == "shared"
    assert "summary" in shared_ambiguous and "next_step" in shared_ambiguous
