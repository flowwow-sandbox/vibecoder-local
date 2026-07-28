#!/usr/bin/env python3
"""PreToolUse: block destructive git operations.

Covers: reset --hard, push --force (включая --force-with-lease), branch -D,
clean -fdx, checkout -- ., interactive rebase, filter-branch.

Таблица «что блокируется» — docs/contracts/safety-rules.md §3.2; список ниже и
та таблица должны совпадать построчно.

Bypass: только CLAUDE_ALLOW_GIT_DESTRUCTIVE=1 в окружении, из которого запущен
агент-тул (см. safety_common.bypass).
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
    bypass,
    read_event,
    strip_git_global_opts,
)

PATTERNS = [
    r"\bgit\s+reset\s+--hard\b",
    # --force-with-lease тоже блокируется: политика пилота запрещает переписывать
    # уже опубликованную историю в любой форме (safety-rules §3), а «вежливый»
    # вариант ломает cross-review ровно так же — ревьюер теряет базу diff'а.
    # Но именно эти две формы, не всё с префиксом `--force-`: `--force-if-includes`
    # ничего не форсит, а требует, чтобы удалённые изменения были влиты локально.
    r"\bgit\s+(push\s+)?(-f|--force(-with-lease)?)(\b|=)(?!-)",
    r"\bgit\s+push\s+.*--force(-with-lease)?(\s|=|$)",
    r"\bgit\s+branch\s+-D\b",
    r"\bgit\s+clean\s+-[fdxX]{2,}",
    r"\bgit\s+clean\s+-[fdx]\s+-[fdx]",
    r"\bgit\s+checkout\s+--\s+\.",
    r"\bgit\s+restore\s+--source",
    r"\bgit\s+restore\s+--staged\s+--worktree\s+\.",
    r"\bgit\s+filter-(branch|repo)\b",
    r"\bgit\s+update-ref\s+-d\s+refs/heads/(main|master|prod(uction)?)",
    # Интерактивный rebase — независимо от того, куда: `-i HEAD~3`, `-i main`,
    # `--interactive origin/main`. Привязка к литеральному HEAD пропускала две
    # последние формы, хотя safety-rules §3.2 обещает блок для всех.
    r"\bgit\s+rebase\b[^\n]*\s(-i|--interactive)(\s|$)",
    r"\bgit\s+reflog\s+expire\s+--expire=now",
    r"\bgit\s+gc\s+--prune=now\s+--aggressive",
]


def main() -> None:
    event = read_event()
    if event.get("tool_name") != "Bash":
        allow()

    cmd = bash_command(event.get("tool_input", {}))
    if not cmd:
        allow()

    # Матчим по команде без глобальных опций (`git -C app push …` → `git push …`),
    # но в лог и в сообщение отдаём исходный текст.
    hit = any_match(strip_git_global_opts(cmd), PATTERNS)
    if not hit:
        allow()

    if bypass("git-destructive", cmd, env_name="CLAUDE_ALLOW_GIT_DESTRUCTIVE"):
        allow()

    block(
        f"Destructive git operation: /{hit}/.\n"
        "Это команды которые перетирают историю или теряют uncommitted работу.\n"
        "Перед выполнением не обходи хук сам:\n"
        "  1) остановись и спроси оунера\n"
        "  2) если он подтвердит — сначала fresh backup branch (git branch backup-...)\n"
        "Безопасные альтернативы:\n"
        "  reset --hard → reset --keep, или stash && reset\n"
        "  push --force (и --force-with-lease) → не нужен: правь fixup-коммитом\n"
        "    в той же feature-ветке, squash-merge всё равно свернёт её историю\n"
        "  branch -D → merge через PR, затем git push origin --delete <branch>\n"
        "  clean -fdx → проверить git status && targeted rm"
    )


if __name__ == "__main__":
    main()
