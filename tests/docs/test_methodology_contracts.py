from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_skill_contains_thin_methodology_sections():
    content = _read(_root() / "SKILL.md")
    assert "## Session Contract" in content
    assert "## Global Guardrails" in content
    assert "## Intent Matrix" in content
    # keep thin guide principle in place
    assert "do not duplicate here" in content


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
