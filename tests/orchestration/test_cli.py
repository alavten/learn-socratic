import json

from scripts import cli


class FakeService:
    def __init__(self):
        self.calls = []

    def list_apis(self):
        self.calls.append(("list_apis", {}))
        return [{"name": "list_apis"}]

    def extend_learning_plan_topics(self, plan_id, topic_ids, reason=None):
        self.calls.append(
            ("extend_learning_plan_topics", {"plan_id": plan_id, "topic_ids": topic_ids, "reason": reason})
        )
        return {"ok": True}

    def append_learning_record(self, plan_id, mode, record_payload):
        self.calls.append(
            ("append_learning_record", {"plan_id": plan_id, "mode": mode, "record_payload": record_payload})
        )
        return {"ok": True}

    def ingest_knowledge_graph(self, graph_id, structured_payload):
        self.calls.append(
            ("ingest_knowledge_graph", {"graph_id": graph_id, "structured_payload": structured_payload})
        )
        return {"ok": True}


def test_cli_list_apis(monkeypatch):
    service = FakeService()
    outputs = []
    monkeypatch.setattr(cli, "create_app", lambda: service)
    monkeypatch.setattr(cli, "_print_json", lambda payload: outputs.append(payload))
    monkeypatch.setattr(cli, "Path", cli.Path)
    monkeypatch.setattr("sys.argv", ["cli.py", "list-apis"])

    cli.main()

    assert outputs == [[{"name": "list_apis"}]]
    assert service.calls == [("list_apis", {})]


def test_cli_extend_topics_splits_csv(monkeypatch):
    service = FakeService()
    outputs = []
    monkeypatch.setattr(cli, "create_app", lambda: service)
    monkeypatch.setattr(cli, "_print_json", lambda payload: outputs.append(payload))
    monkeypatch.setattr(
        "sys.argv",
        [
            "cli.py",
            "extend-learning-plan-topics",
            "--plan-id",
            "p1",
            "--topic-ids",
            "t1, t2,,t3 ",
            "--reason",
            "manual",
        ],
    )

    cli.main()

    assert outputs == [{"ok": True}]
    assert service.calls[0][0] == "extend_learning_plan_topics"
    assert service.calls[0][1]["topic_ids"] == ["t1", "t2", "t3"]


def test_cli_append_record_optional_fields(monkeypatch):
    service = FakeService()
    outputs = []
    monkeypatch.setattr(cli, "create_app", lambda: service)
    monkeypatch.setattr(cli, "_print_json", lambda payload: outputs.append(payload))
    monkeypatch.setattr(
        "sys.argv",
        [
            "cli.py",
            "append-learning-record",
            "--plan-id",
            "p1",
            "--mode",
            "quiz",
            "--concept-id",
            "c1",
            "--result",
            "correct",
            "--score",
            "91",
            "--difficulty-bucket",
            "hard",
            "--latency-ms",
            "1234",
        ],
    )

    cli.main()

    payload = service.calls[0][1]["record_payload"]
    assert payload["concept_id"] == "c1"
    assert payload["score"] == 91.0
    assert payload["difficulty_bucket"] == "hard"
    assert payload["latency_ms"] == 1234
    assert outputs == [{"ok": True}]


def test_cli_ingest_reads_payload_file(monkeypatch, tmp_path):
    service = FakeService()
    outputs = []
    payload = {"graph": {"graph_name": "x"}, "concepts": [], "relations": [], "evidences": [], "relation_evidences": []}
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(cli, "create_app", lambda: service)
    monkeypatch.setattr(cli, "_print_json", lambda p: outputs.append(p))
    monkeypatch.setattr(
        "sys.argv",
        [
            "cli.py",
            "ingest-knowledge-graph",
            "--graph-id",
            "g1",
            "--payload-file",
            str(payload_file),
        ],
    )

    cli.main()

    assert service.calls[0][0] == "ingest_knowledge_graph"
    assert service.calls[0][1]["graph_id"] == "g1"
    assert service.calls[0][1]["structured_payload"]["graph"]["graph_name"] == "x"
    assert outputs == [{"ok": True}]
