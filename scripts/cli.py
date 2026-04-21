"""Unified CLI for doc-socratic orchestration APIs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Support direct execution: `python scripts/cli.py ...`
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.app import create_app


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Doc-Socratic unified CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-apis", help="List available APIs")

    get_api_spec = sub.add_parser("get-api-spec", help="Get API input schema")
    get_api_spec.add_argument("--api-name", required=True)

    list_graphs = sub.add_parser("list-knowledge-graphs", help="List knowledge graphs")
    list_graphs.add_argument("--limit", type=int, default=20)
    list_graphs.add_argument("--cursor")

    get_graph = sub.add_parser("get-knowledge-graph", help="Get knowledge graph detail")
    get_graph.add_argument("--graph-id", required=True)
    get_graph.add_argument("--topic-id")
    get_graph.add_argument("--concept-limit", type=int, default=20)
    get_graph.add_argument("--cursor")

    ingest_graph = sub.add_parser("ingest-knowledge-graph", help="Ingest structured graph payload")
    ingest_graph.add_argument("--graph-id", required=True)
    ingest_graph.add_argument("--payload-file", required=True, help="Path to structured payload JSON")

    list_plans = sub.add_parser("list-learning-plans", help="List learning plans")
    list_plans.add_argument("--limit", type=int, default=20)
    list_plans.add_argument("--cursor")

    create_plan = sub.add_parser("create-learning-plan", help="Create learning plan")
    create_plan.add_argument("--graph-id", required=True)
    create_plan.add_argument("--topic-id")

    extend_plan = sub.add_parser("extend-learning-plan-topics", help="Extend plan topics")
    extend_plan.add_argument("--plan-id", required=True)
    extend_plan.add_argument(
        "--topic-ids",
        required=True,
        help="Comma separated topic IDs, e.g. t1,t2",
    )
    extend_plan.add_argument("--reason")

    learn_prompt = sub.add_parser("get-learning-prompt", help="Get learning prompt")
    learn_prompt.add_argument("--plan-id", required=True)
    learn_prompt.add_argument("--topic-id")

    quiz_prompt = sub.add_parser("get-quiz-prompt", help="Get quiz prompt")
    quiz_prompt.add_argument("--plan-id", required=True)
    quiz_prompt.add_argument("--topic-id")

    review_prompt = sub.add_parser("get-review-prompt", help="Get review prompt")
    review_prompt.add_argument("--plan-id", required=True)
    review_prompt.add_argument("--topic-id")

    append_record = sub.add_parser("append-learning-record", help="Append a learning record")
    append_record.add_argument("--plan-id", required=True)
    append_record.add_argument("--mode", choices=["learn", "quiz", "review"], required=True)
    append_record.add_argument("--concept-id", required=True)
    append_record.add_argument("--result", default="ok")
    append_record.add_argument("--score", type=float)
    append_record.add_argument("--difficulty-bucket", choices=["easy", "medium", "hard"])
    append_record.add_argument("--latency-ms", type=int)

    return parser


def main() -> None:
    args = _parser().parse_args()
    service = create_app()

    if args.command == "list-apis":
        _print_json(service.list_apis())
        return
    if args.command == "get-api-spec":
        _print_json(service.get_api_spec(args.api_name))
        return
    if args.command == "list-knowledge-graphs":
        _print_json(service.list_knowledge_graphs(limit=args.limit, cursor=args.cursor))
        return
    if args.command == "get-knowledge-graph":
        _print_json(
            service.get_knowledge_graph(
                graph_id=args.graph_id,
                topic_id=args.topic_id,
                concept_limit=args.concept_limit,
                cursor=args.cursor,
            )
        )
        return
    if args.command == "ingest-knowledge-graph":
        payload_path = Path(args.payload_file)
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        _print_json(service.ingest_knowledge_graph(graph_id=args.graph_id, structured_payload=payload))
        return
    if args.command == "list-learning-plans":
        _print_json(service.list_learning_plans(limit=args.limit, cursor=args.cursor))
        return
    if args.command == "create-learning-plan":
        _print_json(service.create_learning_plan(graph_id=args.graph_id, topic_id=args.topic_id))
        return
    if args.command == "extend-learning-plan-topics":
        topic_ids = [item.strip() for item in args.topic_ids.split(",") if item.strip()]
        _print_json(
            service.extend_learning_plan_topics(
                plan_id=args.plan_id,
                topic_ids=topic_ids,
                reason=args.reason,
            )
        )
        return
    if args.command == "get-learning-prompt":
        _print_json(service.get_learning_prompt(plan_id=args.plan_id, topic_id=args.topic_id))
        return
    if args.command == "get-quiz-prompt":
        _print_json(service.get_quiz_prompt(plan_id=args.plan_id, topic_id=args.topic_id))
        return
    if args.command == "get-review-prompt":
        _print_json(service.get_review_prompt(plan_id=args.plan_id, topic_id=args.topic_id))
        return
    if args.command == "append-learning-record":
        record_payload: dict[str, Any] = {
            "concept_id": args.concept_id,
            "result": args.result,
        }
        if args.score is not None:
            record_payload["score"] = args.score
        if args.difficulty_bucket is not None:
            record_payload["difficulty_bucket"] = args.difficulty_bucket
        if args.latency_ms is not None:
            record_payload["latency_ms"] = args.latency_ms
        _print_json(
            service.append_learning_record(
                plan_id=args.plan_id,
                mode=args.mode,
                record_payload=record_payload,
            )
        )
        return

    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    main()
