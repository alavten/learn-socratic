from __future__ import annotations

import importlib.util
from pathlib import Path

_REPORTING_PATH = Path(__file__).with_name("reporting.py")
_SPEC = importlib.util.spec_from_file_location("prompt_validation_reporting", _REPORTING_PATH)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

attach_consistency_and_status = _MODULE.attach_consistency_and_status
build_acceptance_report = _MODULE.build_acceptance_report
render_markdown_report = _MODULE.render_markdown_report


def test_reporting_module_is_analysis_only_on_existing_evidence():
    turn_evidence = [
        {
            "user_prompt": "我们先学计算机网络这一章",
            "mode": "learn",
            "assistant_prompt": "Use Feynman loop and Explain, Interpret, Apply.",
            "contract": {"summary": "learned c4", "next_step": "quiz"},
            "commit": {"commit_result": {"concept_id": "se-c4"}},
            "day": "Day1",
        },
        {
            "user_prompt": "基于刚才三个章节，开始测验我",
            "mode": "quiz",
            "assistant_prompt": "Use retrieval-first and SOLO levels.",
            "contract": {"summary": "quiz done", "next_step": "review"},
            "commit": {"commit_result": {"concept_id": "se-c7"}},
            "day": "Day2",
        },
        {
            "user_prompt": "我先给每题一个把握度百分比",
            "mode": "review",
            "assistant_prompt": "Use spacing-first order.",
            "contract": {"summary": "review done", "next_step": "next day plan"},
            "commit": {"commit_result": {"concept_id": "se-c12"}},
            "day": "Day3",
        },
        {
            "user_prompt": "我其实想先回去补一下讲解。",
            "mode": "shared",
            "response": {
                "summary": "intent resolved to learn",
                "next_step": "route_to_learn",
                "clarification_question": "你想先补讲解吗？",
                "resolved_mode": "learn",
            },
            "day": "Day3",
        },
        {
            "user_prompt": "第2天：请补充图谱关系",
            "mode": "ingest",
            "response": {"version": 1, "summary": "ingest ok", "next_step": "learn"},
            "day": "Day1",
        },
        {
            "user_prompt": "第2天：请补充图谱关系（增量）",
            "mode": "ingest",
            "response": {"version": 2, "summary": "ingest ok", "next_step": "learn"},
            "day": "Day2",
        },
    ]
    run_meta = {
        "run_id": "analysis-only-test",
        "executed_at_utc": "2026-04-21T00:00:00+00:00",
        "graph_id": "g-analysis",
        "plan_id": "p-analysis",
        "execution_mode": "SKILL.md 真实提示词会话 / 生产链路观测",
        "used_unit_tests": False,
    }

    report = build_acceptance_report(run_meta=run_meta, turn_evidence=turn_evidence)
    markdown = render_markdown_report(report)
    report = attach_consistency_and_status(report, markdown)

    assert report["execution_mode"] == "SKILL.md 真实提示词会话 / 生产链路观测"
    assert report["used_unit_tests"] is False
    assert report["graph_version_after_first_ingest"] == 1
    assert report["graph_version_after_incremental_ingest"] == 2
    assert report["shared_reroute_evidence"][0]["resolved_mode"] == "learn"
    assert report["shared_reroute_evidence"][0]["has_discovery_snapshot"] is False
    assert report["shared_reroute_evidence"][0]["has_dual_tables"] is False
    assert report["shared_reroute_evidence"][0]["memory_based_phrase_detected"] is False
    assert report["consistency_checks"]["ok"] is True


def test_shared_reroute_flags_memory_only_without_discovery_tables():
    turn_evidence = [
        {
            "user_prompt": "/learn-socratic",
            "mode": "shared",
            "response": {
                "summary": "根据记忆，先选模式",
                "next_step": "ask_mode_choice",
                "clarification_question": "根据记忆，你想进入哪个模式？",
                "resolved_mode": None,
            },
            "day": "Day1",
        }
    ]
    run_meta = {
        "run_id": "shared-memory-only-test",
        "executed_at_utc": "2026-04-21T00:00:00+00:00",
        "graph_id": "g-analysis",
        "plan_id": "p-analysis",
        "execution_mode": "SKILL.md 真实提示词会话 / 生产链路观测",
        "used_unit_tests": False,
    }

    report = build_acceptance_report(run_meta=run_meta, turn_evidence=turn_evidence)
    shared = report["shared_reroute_evidence"][0]
    assert shared["has_discovery_snapshot"] is False
    assert shared["has_dual_tables"] is False
    assert shared["memory_based_phrase_detected"] is True

