#!/usr/bin/env python3
"""PreToolUse: block `git commit --no-verify`.

Pre-commit хуки (gitleaks, lint, тесты) — это часть «Уровня 2 защиты»
пилотного проекта. `--no-verify` обходит все эти проверки и поэтому
запрещён политикой пилота. Bypass через env-var НЕ предусмотрен:
если pre-commit ложно-положительно блокирует коммит, корректное
действие — починить либо саму проверку, либо `.gitleaks.toml`
allowlist, а не глобально снять защиту.

Custom hook (написан для шаблона vibecoder в стиле AnastasiyaW).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from safety_common import (  # noqa: E402
    allow,
    any_match,
    bash_command,
    block,
    log,
    read_event,
)

PATTERNS = [
    r"\bgit\s+commit\b[^\n]*--no-verify\b",
    r"\bgit\s+commit\b[^\n]*\s-n(\s|$)",  # короткая форма -n
    r"\bgit\s+merge\b[^\n]*--no-verify\b",
    r"\bgit\s+push\b[^\n]*--no-verify\b",
    r"\bgit\s+rebase\b[^\n]*--no-verify\b",
]


def main() -> None:
    event = read_event()
    if event.get("tool_name") != "Bash":
        allow()

    cmd = bash_command(event.get("tool_input", {}))
    if not cmd:
        allow()

    hit = any_match(cmd, PATTERNS)
    if not hit:
        allow()

    log("BLOCK", "block_git_no_verify", "deny", hit, cmd)
    block(
        f"Использование `--no-verify` запрещено политикой пилота: /{hit}/.\n"
        "Pre-commit хуки (gitleaks, lint, tests) — часть Уровня 2 защиты.\n"
        "`--no-verify` обходит их все и поэтому НЕ разрешён даже временно.\n"
        "\n"
        "Если pre-commit hook ложно-положительно блокирует коммит:\n"
        "  - gitleaks: добавь паттерн в allowlist в `.gitleaks.toml`\n"
        "  - lint: исправь код или добавь точечный disable-comment\n"
        "  - tests: исправь тест или сам код\n"
        "\n"
        "Bypass через env-var НЕ предусмотрен — это решение пилота.\n"
        "Если хук правда сломан и блокирует валидный коммит — позови\n"
        "ментора, не bypass'ь."
    )


if __name__ == "__main__":
    main()
