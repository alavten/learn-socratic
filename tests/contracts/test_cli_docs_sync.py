import re
import shlex
from pathlib import Path

from scripts.cli import main as cli


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _extract_cli_commands(markdown: str) -> list[str]:
    return re.findall(r"`python -m scripts\.cli\.main ([^`]+)`", markdown)


def _normalize_args(command_tail: str) -> list[str]:
    # Replace doc placeholders so argparse can parse them.
    replaced = (
        command_tail.replace("PLAN_ID", "p1")
        .replace("./payload.json", "payload.json")
        .replace("<path>", "payload.json")
    )
    return shlex.split(replaced)


def test_skill_router_docs_reference_existing_cli_subcommands():
    """CLI copy-paste examples live in SKILL.md so modes/*.md stay free of shell snippets."""
    root = _project_root()
    skill_md = (root / "SKILL.md").read_text(encoding="utf-8")
    parser = cli._parser()

    all_commands = _extract_cli_commands(skill_md)

    assert all_commands, "No CLI commands found in SKILL.md CLI Hints."

    for cmd_tail in all_commands:
        args = _normalize_args(cmd_tail)
        parsed = parser.parse_args(args)
        assert parsed.command
