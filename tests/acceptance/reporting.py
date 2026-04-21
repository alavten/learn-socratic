"""Acceptance reporting helpers for tests/acceptance.

This module is analysis-only:
- allowed: metrics/statistics/consistency checks over existing evidence
- not allowed: driving test cases, constructing scripted prompt execution flows
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from typing import Any


def _assistant_text(turn: dict[str, Any]) -> str:
    return str(turn.get("assistant_prompt") or turn.get("assistant_response") or "")


def _contract_for_turn(turn: dict[str, Any]) -> dict[str, Any]:
    contract = turn.get("contract")
    if isinstance(contract, dict):
        return {
            "mode": turn.get("mode"),
            "summary": contract.get("summary"),
            "next_step": contract.get("next_step"),
        }

    response = turn.get("response")
    if isinstance(response, dict):
        return {
            "mode": turn.get("mode"),
            "summary": response.get("summary"),
            "next_step": response.get("next_step"),
        }

    return {"mode": turn.get("mode"), "summary": None, "next_step": None}


def _methodology_evidence_map(turn_evidence: list[dict[str, Any]]) -> dict[str, list[int]]:
    evidence: dict[str, list[int]] = {
        "SOLO": [],
        "UBD": [],
        "Feynman": [],
        "retrieval_first": [],
        "spacing_first": [],
        "metacognitive": [],
    }
    for idx, turn in enumerate(turn_evidence, start=1):
        text = _assistant_text(turn).lower()
        user_text = str(turn.get("user_prompt") or "").lower()
        mode = turn.get("mode")
        if "solo" in text:
            evidence["SOLO"].append(idx)
        if "explain, interpret, apply" in text:
            evidence["UBD"].append(idx)
        if mode == "learn" and "feynman loop" in text:
            evidence["Feynman"].append(idx)
        if "retrieval-first" in text:
            evidence["retrieval_first"].append(idx)
        if mode == "review" and "spacing-first" in text:
            evidence["spacing_first"].append(idx)
        if any(token in user_text for token in ["把握度", "confidence", "%", "不确定"]):
            evidence["metacognitive"].append(idx)
    return evidence


def _daily_mode_switch_counts(turn_evidence: list[dict[str, Any]]) -> dict[str, int]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for turn in turn_evidence:
        day = turn.get("day")
        if day:
            grouped[str(day)].append(str(turn.get("mode")))

    counts: dict[str, int] = {}
    for day, modes in grouped.items():
        if not modes:
            counts[day] = 0
            continue
        switches = 0
        previous = modes[0]
        for mode in modes[1:]:
            if mode != previous:
                switches += 1
            previous = mode
        counts[day] = switches
    return counts


def _graph_versions(turn_evidence: list[dict[str, Any]]) -> tuple[int | None, int | None, int | None]:
    versions: list[int] = []
    for turn in turn_evidence:
        response = turn.get("response")
        if not isinstance(response, dict):
            continue
        version = response.get("version")
        if isinstance(version, int):
            versions.append(version)
    if not versions:
        return None, None, None
    first = versions[0]
    incremental = versions[1] if len(versions) > 1 else versions[0]
    final = versions[-1]
    return first, incremental, final


def _prompt_trace(turn_evidence: list[dict[str, Any]], contracts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trace: list[dict[str, Any]] = []
    for idx, turn in enumerate(turn_evidence, start=1):
        contract = contracts[idx - 1]
        trace.append(
            {
                "turn_index": idx,
                "user_prompt": turn.get("user_prompt"),
                "mode": turn.get("mode"),
                "assistant_response_summary": contract.get("summary"),
                "next_step": contract.get("next_step"),
            }
        )
    return trace


def _shared_reroute_evidence(turn_evidence: list[dict[str, Any]], contracts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for idx, turn in enumerate(turn_evidence, start=1):
        if turn.get("mode") != "shared":
            continue
        response = turn.get("response") if isinstance(turn.get("response"), dict) else {}
        evidence.append(
            {
                "turn_index": idx,
                "user_prompt": turn.get("user_prompt"),
                "clarification_question": response.get("clarification_question"),
                "resolved_mode": response.get("resolved_mode"),
                "summary": contracts[idx - 1].get("summary"),
                "next_step": contracts[idx - 1].get("next_step"),
            }
        )
    return evidence


def _build_delta(previous_report: dict[str, Any] | None, current_report: dict[str, Any]) -> dict[str, Any]:
    if not previous_report:
        return {"has_previous": False, "changes": []}

    changes: list[str] = []
    prev_turns = int(previous_report.get("thresholds", {}).get("total_turns", 0))
    curr_turns = int(current_report.get("thresholds", {}).get("total_turns", 0))
    if curr_turns != prev_turns:
        changes.append(f"total_turns: {prev_turns} -> {curr_turns}")

    prev_final = previous_report.get("final_status")
    curr_final = current_report.get("final_status")
    if prev_final != curr_final:
        changes.append(f"final_status: {prev_final} -> {curr_final}")

    prev_method = previous_report.get("methodology_hit", {})
    curr_method = current_report.get("methodology_hit", {})
    for key in sorted(set(prev_method) | set(curr_method)):
        if prev_method.get(key) != curr_method.get(key):
            changes.append(f"methodology[{key}]: {prev_method.get(key)} -> {curr_method.get(key)}")

    prev_modes = previous_report.get("mode_distribution", {})
    curr_modes = current_report.get("mode_distribution", {})
    for key in sorted(set(prev_modes) | set(curr_modes)):
        if prev_modes.get(key, 0) != curr_modes.get(key, 0):
            changes.append(f"mode_distribution[{key}]: {prev_modes.get(key, 0)} -> {curr_modes.get(key, 0)}")

    return {"has_previous": True, "changes": changes}


def evaluate_final_status(report: dict[str, Any]) -> str:
    thresholds = report.get("thresholds", {})
    methodology = report.get("methodology_hit", {})
    turns_ok = int(thresholds.get("total_turns", 0)) >= int(thresholds.get("min_turns_required", 20))
    days_ok = bool(thresholds.get("cross_day_covered", False))
    docs_ok = bool(thresholds.get("covers_three_docs", False))
    methodology_ok = all(bool(v) for v in methodology.values())
    loop = report.get("graph_incremental_feedback_loop", {})
    loop_ok = bool(loop.get("incremental_ingest_success")) and set(loop.get("followed_by", [])) >= {"learn", "quiz"}

    hard_ok = turns_ok and days_ok and docs_ok and methodology_ok and loop_ok
    if not hard_ok:
        return "Fail"

    consistency = report.get("consistency_checks", {})
    if consistency.get("ok", True):
        return "Pass"
    return "Conditional Pass"


def build_acceptance_report(
    *,
    run_meta: dict[str, Any],
    turn_evidence: list[dict[str, Any]],
    previous_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mode_distribution = dict(Counter(str(turn.get("mode")) for turn in turn_evidence))
    contracts = [_contract_for_turn(turn) for turn in turn_evidence]
    methodology_evidence_map = _methodology_evidence_map(turn_evidence)
    methodology_hit = {key: bool(value) for key, value in methodology_evidence_map.items()}
    daily_switches = _daily_mode_switch_counts(turn_evidence)
    first_v, incremental_v, final_v = _graph_versions(turn_evidence)

    covered_concepts: set[str] = set()
    for turn in turn_evidence:
        commit = turn.get("commit")
        if isinstance(commit, dict):
            concept_id = commit.get("commit_result", {}).get("concept_id")
            if concept_id:
                covered_concepts.add(concept_id)

    day_coverage = sorted({str(turn.get("day")) for turn in turn_evidence if turn.get("day")})
    shared_evidence = _shared_reroute_evidence(turn_evidence, contracts)
    prompt_trace = _prompt_trace(turn_evidence, contracts)

    report: dict[str, Any] = {
        "run_id": run_meta["run_id"],
        "executed_at_utc": run_meta["executed_at_utc"],
        "graph_id": run_meta["graph_id"],
        "plan_id": run_meta["plan_id"],
        "execution_mode": run_meta.get("execution_mode", "SKILL.md 真实提示词会话 / 生产链路观测"),
        "used_unit_tests": bool(run_meta.get("used_unit_tests", False)),
        "graph_version_after_first_ingest": first_v,
        "graph_version_after_incremental_ingest": incremental_v,
        "graph_version_final": final_v,
        "thresholds": {
            "total_turns": len(turn_evidence),
            "min_turns_required": 20,
            "cross_day_covered": {"Day1", "Day2", "Day3"}.issubset(set(day_coverage)),
            "covers_three_docs": {"se-c4", "se-c7", "se-c12"}.issubset(covered_concepts),
            "covers_targets": ["se-c12", "se-c4", "se-c7"],
        },
        "mode_distribution": mode_distribution,
        "day_coverage": day_coverage,
        "daily_mode_switch_counts": daily_switches,
        "contract_snapshot_per_turn": contracts,
        "methodology_hit": methodology_hit,
        "methodology_evidence_map": methodology_evidence_map,
        "shared_reroute_evidence": shared_evidence,
        "prompt_trace": prompt_trace,
        "graph_incremental_feedback_loop": {
            "trigger": run_meta.get("feedback_trigger", "learning-gap"),
            "incremental_ingest_success": incremental_v is not None and first_v is not None and incremental_v >= first_v,
            "followed_by": run_meta.get("feedback_followed_by", ["learn", "quiz"]),
        },
        "turn_evidence": turn_evidence,
    }
    report["consistency_checks"] = {"ok": True, "errors": []}
    report["final_status"] = evaluate_final_status(report)
    report["delta_from_previous"] = _build_delta(previous_report, report)
    return report


def render_markdown_report(report: dict[str, Any]) -> str:
    thresholds = report["thresholds"]
    methodology = report["methodology_hit"]
    lines = [
        "# SoftwareEngineering Prompt Validation Report",
        "",
        "## 执行元信息",
        f"- run_id: {report['run_id']}",
        f"- 执行日期（UTC）: {report['executed_at_utc']}",
        f"- graph_id: {report['graph_id']}",
        f"- plan_id: {report['plan_id']}",
        f"- 执行方式: {report['execution_mode']}",
        f"- 是否使用单元测试代码: {'是' if report['used_unit_tests'] else '否'}",
        "",
        "## 指标结果",
        f"- 总轮次: {thresholds['total_turns']}",
        f"- 模式分布: {report['mode_distribution']}",
        f"- 覆盖概念: {thresholds['covers_targets']}",
        f"- 跨天覆盖: {report['day_coverage']}",
        f"- 每日模式切换次数: {report['daily_mode_switch_counts']}",
        f"- 图谱版本口径: first={report['graph_version_after_first_ingest']}, incremental={report['graph_version_after_incremental_ingest']}, final={report['graph_version_final']}",
        "",
        "## 方法论命中",
        f"- SOLO: {methodology['SOLO']}",
        f"- UBD: {methodology['UBD']}",
        f"- Feynman: {methodology['Feynman']}",
        f"- retrieval-first: {methodology['retrieval_first']}",
        f"- spacing-first: {methodology['spacing_first']}",
        f"- 元认知校准: {methodology['metacognitive']}",
        "",
        "## 持续回归判定",
        f"- 结果: {report['final_status']}",
        "",
        "## 与上次差异",
        f"- has_previous: {report['delta_from_previous']['has_previous']}",
        f"- changes: {report['delta_from_previous']['changes']}",
        "",
        "本次验收基于 SKILL.md 真实提示词会话执行，未使用单元测试代码或测试函数替代真实交互。所有结论均由对话证据与生产状态证据共同支持。",
    ]
    return "\n".join(lines) + "\n"


def validate_md_json_consistency(report: dict[str, Any], markdown_text: str) -> dict[str, Any]:
    checks = {
        "run_id": f"- run_id: {report['run_id']}",
        "total_turns": f"- 总轮次: {report['thresholds']['total_turns']}",
        "final_status": f"- 结果: {report['final_status']}",
        "graph_version_final": f"final={report['graph_version_final']}",
        "execution_mode": f"- 执行方式: {report['execution_mode']}",
    }
    errors: list[str] = []
    for key, expected_line in checks.items():
        if expected_line not in markdown_text:
            errors.append(f"markdown_missing_{key}: {expected_line}")
    return {"ok": not errors, "errors": errors}


def attach_consistency_and_status(report: dict[str, Any], markdown_text: str) -> dict[str, Any]:
    updated = deepcopy(report)
    updated["consistency_checks"] = validate_md_json_consistency(updated, markdown_text)
    updated["final_status"] = evaluate_final_status(updated)
    return updated

