#!/usr/bin/env python3
"""PreToolUse: block catastrophically destructive shell commands.

Covers: rm -rf on root/home/*, docker/k8s mass delete, mkfs/dd on block devices,
плюс destructive-SQL в адрес ВНЕШНЕЙ БД (safety_common.db_destructive_hit —
локальная SQLite проекта под это не подпадает).

Bypass: только CLAUDE_ALLOW_DESTRUCTIVE=1 в окружении, из которого запущен
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
    db_destructive_hit,
    read_event,
)

# Patterns are regexes. Case-insensitive match via safety_common.any_match.
# `#` входит в терминаторы наравне с концом строки и `;|&`: иначе хвостовой
# комментарий (`rm -rf /etc  # почистим`) уводил команду из-под детекта — то есть
# работал как необъявленный обход хука.
PATTERNS = [
    # Filesystem catastrophes - only truly dangerous paths
    # rm -rf on filesystem root or bare wildcards
    r"\brm\s+-[a-z]*r[a-z]*f?\s+/\s*($|;|&|\||#)",
    r"\brm\s+-[a-z]*r[a-z]*f?\s+/\*",
    r"\brm\s+-[a-z]*r[a-z]*f?\s+\*\s*($|;|&|\||#)",
    # rm -rf on user home
    r"\brm\s+-[a-z]*r[a-z]*f?\s+~\s*($|;|&|\||#|/)",
    r"\brm\s+-[a-z]*r[a-z]*f?\s+\$HOME(\s|$|/)",
    r"\brm\s+-[a-z]*r[a-z]*f?\s+~/\s*($|;|&|\||#)",
    # rm -rf on critical system dirs
    r"\brm\s+-[a-z]*r[a-z]*f?\s+/(etc|usr|var|boot|sys|proc|lib|lib64|sbin|bin|root|home)/?\s*($|;|&|\||#)",
    r"\bfind\s+/\s+.*-delete\b",
    r"\bmkfs\.[a-z0-9]+\s+/dev/",
    r"\bdd\s+if=\S+\s+of=/dev/[sh]d[a-z]",
    r"\b:\s*\(\s*\)\s*\{\s*:\s*\|\s*:",  # fork bomb

    # Destructive SQL здесь НЕ перечисляется: он проверяется отдельно через
    # db_destructive_hit(), который смотрит на клиента БД. Иначе хук ловил бы
    # `sqlite3 app/data/app.db "DROP TABLE …"` (локальная dev-БД пилота) и даже
    # `grep "DROP TABLE" app/migrations` — рутину, а не катастрофу.

    # Container/orchestration mass delete
    r"\bdocker\s+rm\s+-f\s+\$\(docker\s+ps",
    r"\bdocker\s+system\s+prune\s+.*-a.*--volumes",
    r"\bdocker-compose\s+down\s+.*-v",
    r"\bkubectl\s+delete\s+(ns|namespace|all)\b",
    r"\bkubectl\s+delete\s+.*--all\b",
    r"\bhelm\s+uninstall\b.*-n\s+(prod|production)",
]


def main() -> None:
    event = read_event()
    tool_name = event.get("tool_name", "")
    if tool_name != "Bash":
        allow()

    cmd = bash_command(event.get("tool_input", {}))
    if not cmd:
        allow()

    hit = any_match(cmd, PATTERNS) or db_destructive_hit(cmd)
    if not hit:
        allow()

    if bypass("destructive", cmd):
        allow()

    block(
        "Destructive pattern detected: "
        f"/{hit}/. Этот hook блокирует катастрофические операции.\n"
        "Если действие намеренное и обратимость понятна — не обходи хук сам:\n"
        "остановись и спроси оунера (цель + бэкап), решение за ним.\n"
        "Список категорий: rm -rf root/home, destructive-SQL во внешней БД\n"
        "(psql/mysql/mongo/redis-cli — локальная SQLite проекта не считается),\n"
        "kubectl delete all, docker prune --volumes, dd/mkfs."
    )


if __name__ == "__main__":
    main()
