from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (_root() / relative).read_text(encoding="utf-8")


def test_readme_mentions_all_four_modes():
    content = _read("README.md")
    assert "ingest / learn / quiz / review" in content


def test_architecture_mentions_ingest_route_and_naming_convention():
    content = _read("docs/architecture-design.md")
    assert "ingest/learn/quiz/review" in content
    assert "运行时 API 与模式文档优先使用 `snake_case`" in content


def test_coverage_checklist_includes_terminology_rules():
    content = _read("docs/design-coverage-checklist.md")
    assert "## Terminology Consistency" in content
    assert "ingest / learn / quiz / review" in content


def test_runtime_docs_avoid_legacy_camelcase_field_names():
    forbidden = [
        "graphId",
        "conceptId",
        "topicId",
        "planId",
        "sessionId",
        "recordType",
        "difficultyBucket",
        "occurredAt",
        "nextReviewAt",
        "priorityScore",
        "dueAt",
        "reasonType",
        "createdAt",
        "updatedAt",
    ]
    root = _root()
    violations: list[str] = []
    for md_path in root.rglob("*.md"):
        relative = md_path.relative_to(root).as_posix()
        if relative == "docs/data-model-design.md":
            continue
        content = md_path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in content:
                violations.append(f"{relative}: {token}")
    assert violations == []
