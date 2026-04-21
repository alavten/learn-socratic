from __future__ import annotations

import re
from pathlib import Path


def chapter_num(path: Path) -> int:
    match = re.search(r"Chapter(\d+)-", path.name)
    return int(match.group(1)) if match else 9999


def extract_first_paragraph(markdown: str) -> str:
    lines = markdown.splitlines()
    chunks: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if chunks:
                break
            continue
        if stripped.startswith(("#", "|", "```", "-", "*", ">")):
            continue
        chunks.append(stripped)
        if len(" ".join(chunks)) >= 140:
            break
    text = " ".join(chunks).strip()
    return text[:220] if text else "Core software engineering concept for exam preparation."


def build_software_engineering_payload(chapter_dir: Path) -> dict:
    chapter_files = sorted(chapter_dir.glob("Chapter*.md"), key=chapter_num)
    assert chapter_files, "No software engineering chapter files found"

    topics = []
    concepts = []
    topic_concepts = []
    relations = []
    evidences = []
    relation_evidences = []

    for idx, chapter_file in enumerate(chapter_files, start=1):
        content = chapter_file.read_text(encoding="utf-8")
        title_line = next((line for line in content.splitlines() if line.startswith("# ")), chapter_file.stem)
        title = title_line.removeprefix("# ").strip()
        concept_id = f"se-c{idx}"
        topic_id = f"se-t{idx}"
        evidence_id = f"se-e{idx}"

        topics.append(
            {
                "topic_id": topic_id,
                "topic_name": title,
                "topic_type": "chapter",
                "sort_order": idx,
            }
        )
        concepts.append(
            {
                "concept_id": concept_id,
                "canonical_name": title,
                "definition": extract_first_paragraph(content),
                "concept_type": "exam_knowledge",
                "difficulty_level": "medium",
            }
        )
        topic_concepts.append(
            {
                "topic_concept_id": f"se-tc{idx}",
                "topic_id": topic_id,
                "concept_id": concept_id,
                "role": "core",
                "rank": 1,
            }
        )
        evidences.append(
            {
                "evidence_id": evidence_id,
                "source_type": "doc",
                "source_title": title,
                "source_uri": str(chapter_file),
                "quote_text": extract_first_paragraph(content),
            }
        )

        if idx > 1:
            relation_id = f"se-r{idx-1}"
            relations.append(
                {
                    "concept_relation_id": relation_id,
                    "from_concept_id": f"se-c{idx-1}",
                    "to_concept_id": concept_id,
                    "relation_type": "related_to",
                }
            )
            relation_evidences.append(
                {
                    "relation_evidence_id": f"se-re{idx-1}",
                    "concept_relation_id": relation_id,
                    "evidence_id": evidence_id,
                    "support_score": 0.8,
                }
            )

    return {
        "graph": {
            "graph_type": "domain",
            "graph_name": "Software Engineering Exam Knowledge",
            "schema_version": "1.0.0",
            "release_tag": "se-r1",
        },
        "topics": topics,
        "concepts": concepts,
        "topic_concepts": topic_concepts,
        "relations": relations,
        "evidences": evidences,
        "relation_evidences": relation_evidences,
    }
