import re
import shlex
from pathlib import Path

from scripts import cli


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _extract_cli_commands(markdown: str) -> list[str]:
    return re.findall(r"`python scripts/cli\.py ([^`]+)`", markdown)


def _normalize_args(command_tail: str) -> list[str]:
    # Replace doc placeholders so argparse can parse them.
    replaced = (
        command_tail.replace("PLAN_ID", "p1")
        .replace("./payload.json", "payload.json")
        .replace("<path>", "payload.json")
    )
    return shlex.split(replaced)


def test_mode_docs_reference_existing_cli_subcommands():
    root = _project_root()
    mode_files = [
        root / "modes" / "shared.md",
        root / "modes" / "ingest.md",
        root / "modes" / "learn.md",
        root / "modes" / "quiz.md",
        root / "modes" / "review.md",
    ]
    parser = cli._parser()

    all_commands: list[str] = []
    for file in mode_files:
        markdown = file.read_text(encoding="utf-8")
        all_commands.extend(_extract_cli_commands(markdown))

    assert all_commands, "No CLI commands found in mode docs."

    for cmd_tail in all_commands:
        args = _normalize_args(cmd_tail)
        parsed = parser.parse_args(args)
        assert parsed.command
