#!/usr/bin/env python3
"""Fetch ALL concepts from se-full-20260422 knowledge graph via paginated CLI calls."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

GRAPH_ID = "se-full-20260422"
CONCEPT_LIMIT = 200
OUTPUT_PATH = Path("/tmp/se-full-all.json")
CWD = Path(__file__).resolve().parent


def _fetch_page(offset: int) -> dict:
    cmd = [
        sys.executable, "-m", "scripts.cli.main",
        "get-knowledge-graph",
        "--graph-id", GRAPH_ID,
        "--concept-limit", str(CONCEPT_LIMIT),
        "--offset", str(offset),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(CWD))
    data = json.loads(result.stdout)
    return data


def main() -> None:
    all_topic_concepts: list[dict] = []
    all_concept_briefs: list[dict] = []
    topics: list[dict] | None = None
    graph_meta: dict | None = None
    offset = 0
    page = 0

    while True:
        page += 1
        data = _fetch_page(offset)
        print(f"Page {page}: offset={offset}, "
              f"tc={len(data['topic_concepts'])}, "
              f"cb={len(data['concept_briefs'])}, "
              f"has_more={data['has_more']}")

        all_topic_concepts.extend(data["topic_concepts"])
        all_concept_briefs.extend(data["concept_briefs"])

        if topics is None:
            topics = data["topics"]
            graph_meta = data["graph"]

        if not data["has_more"]:
            break

        offset = data["next_offset"]

    # Organise by topic_id
    by_topic: dict[str, list[dict]] = {}
    for tc in all_topic_concepts:
        by_topic.setdefault(tc["topic_id"], []).append(tc)

    topic_map = {t["topic_id"]: t for t in topics}
    sorted_topic_ids = sorted(
        by_topic.keys(),
        key=lambda tid: (topic_map.get(tid, {}).get("sort_order", 999), tid),
    )

    output = {
        "graph": graph_meta,
        "summary": {
            "total_concepts": len(all_topic_concepts),
            "unique_concept_briefs": len(all_concept_briefs),
            "total_topics": len(by_topic),
            "all_topics_in_graph": len(topics),
        },
        "topics": [
            {
                "topic_id": tid,
                **topic_map.get(tid, {}),
                "concept_count": len(by_topic[tid]),
                "concepts": by_topic[tid],
            }
            for tid in sorted_topic_ids
        ],
        "concept_briefs": all_concept_briefs,
    }

    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {OUTPUT_PATH}  ({OUTPUT_PATH.stat().st_size:,} bytes)")
    print(f"Total topic_concepts: {len(all_topic_concepts)}")
    print(f"Unique concept_briefs: {len(all_concept_briefs)}")
    print(f"Topics with concepts: {len(by_topic)}")
    print(f"Total topics in graph: {len(topics)}")

    # Per-topic breakdown
    print("\n=== Per-topic concept counts ===")
    for tid in sorted_topic_ids:
        info = topic_map.get(tid, {})
        name = info.get("topic_name", tid)
        ttype = info.get("topic_type", "?")
        so = info.get("sort_order", "?")
        count = len(by_topic[tid])
        print(f"  [{so:>2}] {tid:<20s} ({ttype:>8s}) {count:>4d} concepts  {name}")

    # Chapter hierarchy
    print("\n=== Chapter hierarchy ===")
    chapters = [t for t in topics if t.get("topic_type") == "chapter"]
    chapters.sort(key=lambda t: (t.get("sort_order", 999), t["topic_id"]))
    for ch in chapters:
        ch_id = ch["topic_id"]
        ch_name = ch["topic_name"]
        so = ch.get("sort_order", "?")
        print(f"  [{so:>2}] {ch_id}  {ch_name}")
        subs = [t for t in topics if t.get("parent_topic_id") == ch_id]
        subs.sort(key=lambda t: (t.get("sort_order", 999), t["topic_id"]))
        for s in subs:
            print(f"       └─ {s['topic_id']:>20s}  {s['topic_name']}")

    orphan_sections = [t for t in topics if t.get("topic_type") in ("section",) and t.get("parent_topic_id") is None]
    orphan_sections.sort(key=lambda t: (t.get("sort_order", 999), t["topic_id"]))
    if orphan_sections:
        print(f"\n  Top-level sections (no parent): {len(orphan_sections)}")
        for s in orphan_sections:
            print(f"    [{s.get('sort_order', '?')}] {s['topic_id']}  {s['topic_name']}")


if __name__ == "__main__":
    main()
