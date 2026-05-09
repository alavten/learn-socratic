from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_skill_contains_thin_methodology_sections():
    content = _read(_root() / "SKILL.md")
    assert ("## Session Contract" in content) or ("## Session Guardrails" in content)
    assert ("## Global Guardrails" in content) or ("Keep this file thin:" in content)
    assert "## Intent Matrix" in content
    # keep thin guide principle in place
    assert ("do not duplicate here" in content) or ("mode-specific fields/steps live only" in content)


def test_modes_define_experience_contract_sections():
    root = _root() / "modes"
    mode_files = ["ingest.md", "learn.md", "quiz.md", "review.md"]
    for name in mode_files:
        content = _read(root / name)
        assert "## AI Execution Directives" in content
        assert "## Turn Contract" in content
        assert "## Escalation Rule" in content
        assert "## Mode Exit Rule" in content
        assert "## Evidence Rule" in content


def test_modes_output_contract_has_summary_and_next_step():
    root = _root() / "modes"
    mode_files = ["shared.md", "ingest.md", "learn.md", "quiz.md", "review.md"]
    for name in mode_files:
        content = _read(root / name)
        assert "summary" in content
        assert "next_step" in content


def test_shared_and_learn_require_discovery_snapshot_and_dual_tables():
    root = _root() / "modes"
    shared = _read(root / "shared.md")
    learn = _read(root / "learn.md")

    assert "discovery_snapshot" in shared
    assert "knowledge_graphs_table" in shared
    assert "pending_learning_plans_table" in shared
    assert "choose **plan** or **graph** first" in shared

    assert "route to `shared`" in learn
    assert "discovery tables" in learn.lower()


def test_modes_require_per_turn_record_write_and_no_progress_on_write_failure():
    root = _root() / "modes"
    learn = _read(root / "learn.md")
    quiz = _read(root / "quiz.md")
    review = _read(root / "review.md")

    assert "MUST: after each concept check answer is received, write record immediately" in learn
    assert "do not advance to next concept/question" in learn

    assert "MUST: after each learner answer is judged, write record immediately" in quiz
    assert "no next question in same turn" in quiz

    assert "MUST: after each learner answer is judged, write record immediately before queue advance/next question" in review
    assert "only after successful record write" in review
