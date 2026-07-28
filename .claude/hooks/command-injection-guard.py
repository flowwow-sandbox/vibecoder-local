#!/usr/bin/env python3
"""PreToolUse: detect suspicious shell substitution in Bash commands.

Targets the class of bugs where text meant as data becomes command:
  gh issue create --body "$(dropdb prod)"
  echo "result: $(rm -rf /tmp)" > log.txt

Here the outer command is safe (gh, echo), but $(...) executes before
arg gets to the outer command. This class is distinct from block_destructive
which catches naked 'dropdb'; here we catch 'dropdb' smuggled inside a string.

Strategy:
  - Trivial substitutions are allowed: $(pwd), $(date), $(whoami), $(hostname),
    $(basename ...), $(dirname ...), $(echo ...), $(uname ...)
  - Substitution containing destructive verbs → hard block
  - Other substitutions → advisory block (pass with confirmation)

Bypass: CLAUDE_ALLOW_INJECTION=1.
"""
from __future__ import annotations

import os.path
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from safety_common import (  # noqa: E402
    allow,
    bash_command,
    block,
    bypass,
    db_destructive_hit,
    log,
    read_event,
)

# Well-known side-effect-free utilities safe inside $(...)
# Опасен не факт подстановки, а destructive-глагол внутри неё — его ловят
# DESTRUCTIVE_VERBS и db_destructive_hit, которые проверяются РАНЬШЕ этого списка.
TRIVIAL_CMDS = {
    "pwd", "date", "whoami", "hostname", "id", "uname", "echo", "printf",
    "basename", "dirname", "realpath", "readlink",
    "cat", "head", "tail",  # reads; add only if they take trivial args
    "which", "command", "type",
    "tr", "cut", "wc", "sort", "uniq", "grep", "rg", "ls",
    "git",  # git rev-parse etc is common and safe
    "node", "python", "python3",  # when running --version
    "jq",
    "mktemp",  # $(mktemp -d) — канон для scratch-каталога
}

# Пакетные менеджеры и toolchain целиком в TRIVIAL_CMDS класть нельзя: рутинный
# `$(npm pkg get version)` и разрушительный `$(npm publish)` — один исполняемый
# файл. Поэтому whitelist на уровне подкоманды: всё, чего здесь нет, остаётся
# non-trivial и требует подтверждения. `sed`/`awk` не в списках вовсе — `sed -i`
# правит файл на месте, `awk` умеет system().
#
# Двусловные записи («pkg get», «python find») нужны там, где подкоманда сама по
# себе неоднородна: `npm pkg get` читает package.json, а `npm pkg set|delete` его
# правит; `uv python find` ищет интерпретатор, `uv python install` ставит его.
TRIVIAL_SUBCOMMANDS = {
    "brew": {"--prefix", "--cellar", "--repository", "--version", "list", "info"},
    "npm": {"pkg get", "view", "ls", "list", "root", "prefix", "bin", "--version", "-v"},
    "pnpm": {"list", "ls", "root", "bin", "--version", "-v"},
    "yarn": {"list", "info", "--version", "-v"},
    "bun": {"pm ls", "--version", "-v", "--revision"},
    # `uv tree` без --frozen/--locked резолвит проект и может переписать uv.lock;
    # `uv python find X` при отсутствии интерпретатора скачивает и ставит его.
    # Обе — правка состояния окружения, а не диагностика.
    "uv": {"python list", "--version", "-V"},
    "pip": {"show", "list", "--version"},
    "pip3": {"show", "list", "--version"},
}

# Каталоги, из которых исполняемый считается «той самой системной утилитой».
# Совпадение basename'а недостаточно: `$(./ls …)` и `$(/tmp/jq …)` — чужой код
# под знакомым именем, он должен оставаться non-trivial.
TRUSTED_BIN_DIRS = (
    "/bin/", "/sbin/", "/usr/bin/", "/usr/sbin/", "/usr/local/bin/",
    "/opt/homebrew/bin/", "/opt/local/bin/",
)

# Флаги, из-за которых «безобидная» утилита перестаёт быть таковой:
#   rg --pre CMD          — спавнит CMD на каждый просматриваемый файл;
#   jq --rawfile x .env   — втягивает содержимое файла в вывод (обход secret-guard);
#   mktemp --tmpdir=DIR   — создаёт файл вне /tmp и вне проекта.
EXEC_BEARING_FLAGS = {
    "rg": re.compile(r"(?:^|\s)--(?:pre|hostname-bin)(?:\s|=)"),
    # --rawfile втягивает файл в вывод; фильтр `env` / `$ENV` выгружает всё
    # окружение процесса агента, где живут ключи. `.env` как поле JSON — не в
    # счёт, поэтому перед `env` не должно быть точки.
    "jq": re.compile(r"(?:^|\s)--(?:rawfile|slurpfile|argfile)(?:\s|=)|(?<![.\w])env\b|\$ENV\b"),
    "mktemp": re.compile(r"(?:^|\s)(?:--tmpdir(?:=|\s)|-p(?:\s|=))"),
}

SUBST_REGEX = re.compile(r"\$\(([^()]*(?:\([^()]*\)[^()]*)*)\)")
BACKTICK_REGEX = re.compile(r"`([^`]+)`")
# Quoted-heredoc body: <<'EOF' / <<"EOF" / <<-'EOF' opener, then literal text up to
# a line whose only content is the delimiter. Quoted delimiter ⇒ no shell expansion
# inside ⇒ safe to strip before substitution scanning (see find_substitutions).
QUOTED_HEREDOC_REGEX = re.compile(r"<<-?\s*(['\"])(\w+)\1.*?\n[ \t]*\2\b", re.DOTALL)

# Destructive SQL здесь не перечисляется — он проверяется через
# db_destructive_hit() по клиенту БД (см. safety_common), иначе подстановка
# `$(grep -c "DROP TABLE" app/migrations/001.sql)` считалась бы катастрофой.
DESTRUCTIVE_VERBS = re.compile(
    r"\b("
    r"rm\s+-[rf]+"
    r"|mkfs\.|dd\s+if=|dd\s+of=/dev/"
    r"|kubectl\s+delete"
    r"|docker\s+(rm\s+-f|system\s+prune)"
    r"|killall|pkill"
    r"|shutdown|reboot|halt|poweroff"
    r"|:\s*\(\s*\)\s*\{"  # fork bomb
    r"|curl\s+.*\|\s*(sh|bash)"  # pipe to shell
    r"|wget\s+.*\|\s*(sh|bash)"
    r")",
    re.IGNORECASE,
)


def is_trivial(subst_body: str) -> bool:
    """Check if the substitution body is a safe utility with safe args."""
    body = subst_body.strip()
    if not body:
        return True
    # Heredoc forms: $(cat <<EOF ... EOF) or $(cat <<'EOF' ... EOF) -
    # safely reads multiline literal text into a string. No execution.
    if re.match(r"^(cat|printf|echo)\s+<<", body) or re.match(r"^<<", body):
        return True
    # First word determines the utility
    tokens = body.split()
    first = tokens[0].lstrip("\\")  # strip leading escape
    if "/" in first:
        # Путь к исполняемому: имя утилиты засчитываем только из системных
        # каталогов (/opt/homebrew/bin/brew — да, ./ls и /tmp/jq — нет).
        # normpath обязателен: лексический префикс проходил на traversal
        # `/usr/bin/../../tmp/jq`, который ОС резолвит в /tmp/jq.
        resolved = os.path.normpath(first)
        if not resolved.startswith(TRUSTED_BIN_DIRS):
            return False
        first = resolved.rsplit("/", 1)[-1]
    exec_flags = EXEC_BEARING_FLAGS.get(first)
    if exec_flags and exec_flags.search(body):
        return False
    if first in TRIVIAL_SUBCOMMANDS:
        # Пакетный менеджер: доверяем не файлу, а конкретной read-only подкоманде.
        # Проверяем и двусловную форму («npm pkg get»), и однословную.
        allowed = TRIVIAL_SUBCOMMANDS[first]
        two = " ".join(tokens[1:3])
        one = tokens[1] if len(tokens) > 1 else ""
        if two not in allowed and one not in allowed:
            return False
    elif first not in TRIVIAL_CMDS:
        return False
    # Extra check: even trivial cmd with shell metacharacters in args is suspect.
    # But <<- and << are heredoc markers, not pipes/redirects - allow.
    if re.search(r"[;&|](?!\|)", body):  # ; & | (but not ||)
        return False
    if re.search(r"[<>](?!<)", body):  # < or > but not << (heredoc)
        return False
    return True


def find_substitutions(cmd: str) -> list[tuple[str, str]]:
    """Return list of (form, body) for each substitution in cmd.

    form: '$()' or '``'
    body: inner text
    """
    found: list[tuple[str, str]] = []
    # Drop quoted-heredoc bodies first: <<'EOF' … EOF / <<"EOF" … EOF / <<-'EOF' …
    # are LITERAL — the shell performs no $()/backtick expansion inside them. This
    # is the common `gh pr create --body "$(cat <<'EOF' … EOF)"` form, where
    # markdown inline-code like `CODEX_AUTH` must not be mis-read as a command
    # substitution. Unquoted <<EOF DOES expand, so it is deliberately NOT stripped.
    # Must run before the single-quote pass below, which would mangle the <<'DELIM'.
    sanitized = QUOTED_HEREDOC_REGEX.sub("<<HEREDOC", cmd)
    # Skip single-quoted regions since $(...) is literal inside '...'
    # Approximate: remove content between unescaped single quotes
    sanitized = re.sub(r"'[^']*'", "''", sanitized)
    for m in SUBST_REGEX.finditer(sanitized):
        found.append(("$()", m.group(1)))
    for m in BACKTICK_REGEX.finditer(sanitized):
        found.append(("``", m.group(1)))
    return found


def main() -> None:
    event = read_event()
    if event.get("tool_name") != "Bash":
        allow()

    cmd = bash_command(event.get("tool_input", {}))
    if not cmd:
        allow()

    substitutions = find_substitutions(cmd)
    if not substitutions:
        allow()

    # Check each substitution
    destructive_hits: list[str] = []
    nontrivial_hits: list[str] = []
    for form, body in substitutions:
        if DESTRUCTIVE_VERBS.search(body) or db_destructive_hit(body):
            destructive_hits.append(f"{form} -> {body[:80]}")
        elif not is_trivial(body):
            nontrivial_hits.append(f"{form} -> {body[:80]}")

    if not destructive_hits and not nontrivial_hits:
        allow()

    if bypass("injection", cmd):
        pattern = destructive_hits[0] if destructive_hits else nontrivial_hits[0]
        log("WARN", "block_command_injection", "bypass", pattern, cmd)
        allow()

    # Destructive substitution = always block
    if destructive_hits:
        log("BLOCK", "block_command_injection", "deny_destructive",
            destructive_hits[0], cmd)
        block(
            "Destructive shell substitution detected inside command:\n"
            f"  {destructive_hits[0]}\n"
            "Это класс багов когда текст который должен быть данными исполняется\n"
            "как команда из-за неверно escaped кавычек. Пример из практики:\n"
            "  gh issue create --body \"...$(dropdb prod)...\"\n"
            "Подстановка $() выполняется ДО того как аргумент попадает в gh.\n"
            "Что делать:\n"
            "  - использовать одинарные кавычки чтобы сделать $() literal\n"
            "  - передать текст через stdin: printf '...' | gh ...\n"
            "  - использовать --body-file вместо inline --body\n"
            "  - пишешь содержимое файла? используй Edit/Write/apply_patch, не shell\n"
            "  - сомневаешься — остановись и спроси оунера; сам хук не обходи"
        )

    # Non-trivial but non-destructive = advisory block
    log("BLOCK", "block_command_injection", "deny_nontrivial",
        nontrivial_hits[0], cmd)
    block(
        f"Non-trivial shell substitution: {nontrivial_hits[0]}\n"
        "Подстановка с side effects. Подтверди что она намеренная.\n"
        "Trivial substitutions (pwd, date, whoami, basename, dirname, echo) проходят.\n"
        "Пишешь содержимое файла? используй Edit/Write/apply_patch, не shell-heredoc.\n"
        "Сомневаешься — остановись и спроси оунера; сам хук не обходи."
    )


if __name__ == "__main__":
    main()
