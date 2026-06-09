from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


FIVE_SECTION_HEADERS = (
    "## 适用场景",
    "## 前置输入",
    "## 执行步骤",
    "## 停止条件",
    "## 下一步调整",
)

LEGACY_SECTIONS = (
    "## AI Execution Directives",
    "## Turn Contract",
    "## Escalation Rule",
    "## Mode Exit Rule",
    "## Evidence Rule",
    "## Queue Policy",
    "## Runtime Execution Chain",
    "## Trigger Conditions",
)


def test_skill_contains_thin_methodology_sections():
    content = _read(_root() / "SKILL.md")
    assert ("## Session Contract" in content) or ("## Session Guardrails" in content)
    assert ("## Global Guardrails" in content) or ("Keep this file thin:" in content)
    assert "## Intent Matrix" in content
    assert ("do not duplicate here" in content) or ("mode-specific fields/steps live only" in content)


def test_mode_files_use_five_section_template():
    root = _root() / "references"
    mode_files = ["ingest.md", "learn.md", "quiz.md", "review.md", "shared.md"]
    for name in mode_files:
        content = _read(root / name)
        for header in FIVE_SECTION_HEADERS:
            assert header in content, f"{name} missing {header}"
        for legacy in LEGACY_SECTIONS:
            assert legacy not in content, f"{name} still contains legacy section {legacy}"


def test_modes_output_contract_has_summary_and_next_step():
    root = _root() / "references"
    mode_files = ["shared.md", "ingest.md", "learn.md", "quiz.md", "review.md"]
    for name in mode_files:
        content = _read(root / name)
        assert "summary" in content
        assert "next_step" in content


def test_shared_has_mode_selection_table():
    shared = _read(_root() / "references" / "shared.md")
    assert "| Mode |" in shared
    assert "ingest.md" in shared
    assert "learn.md" in shared
    assert "quiz.md" in shared
    assert "review.md" in shared


def test_learn_routes_to_shared_when_plan_missing():
    learn = _read(_root() / "references" / "learn.md")
    assert "shared" in learn
    assert "plan_id" in learn


def test_reorder_topics_file_removed():
    assert not (_root() / "references" / "reorder-topics.md").exists()


def test_skill_intent_matrix_routes_reorder_to_ingest():
    content = _read(_root() / "SKILL.md")
    assert "references/ingest.md" in content
    assert "reorder-topics.md" not in content


def test_skill_requires_interaction_record_and_has_no_global_write_gate():
    content = _read(_root() / "SKILL.md")
    lowered = content.lower()
    assert "do not call write/mutation apis without explicit user confirmation" not in lowered
    assert "add_interaction_record" in content
    assert "learning telemetry" in lowered
    assert "After each taught concept or judged learner answer" in content
    assert "until the previous record write succeeds or recovery is surfaced" in content


def test_ingest_includes_reorder_subflow():
    ingest = _read(_root() / "references" / "ingest.md")
    assert "reorder-graph-topics" in ingest
    assert "书序修正" in ingest
