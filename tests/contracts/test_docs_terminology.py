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
    assert "ingest / learn / quiz / review" in content or "ingest/learn/quiz/review" in content
    assert "kebab-case" in content
    assert "API_SPECS" in content


def test_architecture_includes_terminology_rules():
    content = _read("docs/architecture-design.md")
    assert "## 9. 质量门禁与验收" in content
    assert "ingest / learn / quiz / review" in content
    assert "snake_case" in content


def test_only_architecture_design_doc_in_docs():
    docs_dir = _root() / "docs"
    md_files = sorted(p.name for p in docs_dir.glob("*.md"))
    assert md_files == ["architecture-design.md"]


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
        if relative == "docs/architecture-design.md":
            continue
        content = md_path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in content:
                violations.append(f"{relative}: {token}")
    assert violations == []
