#!/usr/bin/env python3
"""PreToolUse: block writes outside the project root.

Часть «Уровня 2 защиты» пилотного проекта vibecoder. Идея простая:
агент должен писать только в репозиторий проекта (и в общеизвестные
tmp-локации). Случайный `rm /Users/foo/...` или `Write` в `/etc/...`
почти всегда означает, что агент потерялся — лучше заблокировать.

Стратегия:
  - Edit/Write/NotebookEdit: target file_path должен быть внутри корня
    репо (или внутри ALLOWED_WRITE_DIRS).
  - Bash: блокируем только write-команды (rm, mv, cp с destination,
    редиректы > / >>, mkdir, touch, tee, sed -i, dd of=, tar -x в
    target dir и т.п.) с абсолютными путями вне корня. Read-команды
    (cat, ls, which, brew install — read package, find без -delete)
    пропускаем — иначе ломается legitimate workflow.

Bypass: CLAUDE_ALLOW_WORKDIR=1.

Custom hook (написан для шаблона vibecoder в стиле AnastasiyaW).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from safety_common import (  # noqa: E402
    allow,
    apply_patch_targets,
    bash_command,
    block,
    bypass,
    file_path,
    log,
    read_event,
)

# Tmp-локации, в которые писать всегда можно (агент использует их легитимно
# для распакованных архивов, scratch-файлов и т.п.).
ALLOWED_WRITE_DIRS = [
    "/tmp",
    "/var/tmp",
    "/private/tmp",
    "/private/var/tmp",
    "/var/folders",          # macOS NSTemporaryDirectory
    "/private/var/folders",
    "/dev/null",
    "/dev/stdout",
    "/dev/stderr",
]

# Bash-команды, чьи аргументы трактуем как «target пишется». Если такая
# команда содержит абсолютный путь вне репо/tmp — блок.
WRITE_VERBS_REGEX = re.compile(
    r"\b("
    r"rm|rmdir|mv|cp|install|ln"
    r"|mkdir|touch|tee"
    r"|chmod|chown|chgrp"
    r"|truncate"
    r"|dd"
    r")\b",
    re.IGNORECASE,
)

# Редирект `> path` или `>> path` — abs или relative. Капчурим путь.
REDIRECT_REGEX = re.compile(r"(?<![<>])(?:>>?|&>>?)\s*([^\s;|&)<>]+)")

# `sed -i ...` редактирует файл in-place — отдельная регулярка.
SED_INPLACE_REGEX = re.compile(r"\bsed\s+(?:[^|;&\n]*\s)?-i(?:\.\w+)?\b")

# `dd of=/dev/...` — отдельный паттерн, чтобы и read и write совпали.
DD_OF_REGEX = re.compile(r"\bdd\b[^|;&\n]*\bof=(/[^\s;|&)<>]+)")


def _project_root() -> Path:
    """Find project root: try `git rev-parse --show-toplevel`, fallback to cwd."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        if result.returncode == 0:
            top = result.stdout.strip()
            if top:
                return Path(top).resolve()
    except (OSError, subprocess.SubprocessError):
        pass
    return Path(os.getcwd()).resolve()


def _path_is_allowed(target: str, root: Path) -> bool:
    """True if target is inside project root or an allowed tmp-location."""
    if not target:
        return True  # nothing to check
    try:
        resolved = Path(target).expanduser().resolve()
    except (OSError, ValueError):
        return True  # cannot resolve → don't false-positive
    resolved_str = str(resolved)
    root_str = str(root)
    # Inside project root
    if resolved_str == root_str or resolved_str.startswith(root_str + os.sep):
        return True
    # Allowed tmp/dev locations
    for allowed in ALLOWED_WRITE_DIRS:
        if resolved_str == allowed or resolved_str.startswith(allowed + os.sep):
            return True
    return False


def _canonicalize(token: str) -> str:
    """Resolve token to absolute path: expand ~, then resolve relative to cwd."""
    p = Path(token).expanduser()
    if not p.is_absolute():
        p = Path(os.getcwd()) / p
    return str(p.resolve())


def _extract_write_targets(cmd: str) -> list[tuple[str, str]]:
    """For a bash command, return list of (verb, abs_path) that look like write targets.

    Heuristic — намеренно консервативная, чтобы не ломать legitimate workflow:
      - редиректы `> path` и `>> path` — всегда write (abs или relative).
      - `sed -i /abs/path` — write.
      - `dd of=/abs/path` — write.
      - `rm/mv/cp/mkdir/touch/...` + path (abs или relative) среди аргументов — write.
    Если первый токен команды НЕ из WRITE_VERBS — пропускаем (read-only либо
    неизвестно, лучше allow чем ложно-блокировать `which /usr/bin/python3`).

    Relative paths (включая `../` traversal) канонизируются через cwd, чтобы
    `echo x > ../../other-repo/file` корректно детектировалось как write outside root.
    """
    targets: list[tuple[str, str]] = []

    # Redirects: > path или >> path (abs или relative, но не пустые/флаги).
    for m in REDIRECT_REGEX.finditer(cmd):
        token = m.group(1).strip("\"'")
        # Пропускаем fd-редиректы типа `2>&1`, `>&2`
        if re.match(r"^[0-9&-]", token):
            continue
        targets.append((">", _canonicalize(token)))

    # sed -i (path после флагов).
    if SED_INPLACE_REGEX.search(cmd):
        # Любой /abs/path в этой команде считаем write-target.
        for m in re.finditer(r"(?:^|\s)(/[^\s;|&)<>]+)", cmd):
            targets.append(("sed -i", m.group(1)))

    # dd of=...
    for m in DD_OF_REGEX.finditer(cmd):
        targets.append(("dd of=", m.group(1)))

    # Write-verbs c путями (abs и relative). Анализируем посегментно (по `;`, `&&`,
    # `||`, `|`), чтобы первый токен сегмента означал «команда».
    segments = re.split(r"(?:;|&&|\|\||\|)", cmd)
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        # Первое слово = команда (с возможным префиксом sudo/env)
        tokens = seg.split()
        verb = None
        for tok in tokens:
            if tok in {"sudo", "env", "nohup", "exec", "time"}:
                continue
            # "VAR=value cmd" — пропускаем env assignment
            if "=" in tok and not tok.startswith("/"):
                continue
            verb = tok
            break
        if not verb:
            continue
        if not WRITE_VERBS_REGEX.search(verb):
            continue
        # Собираем пути среди аргументов (abs, relative, ~/...)
        for tok in tokens[1:]:
            tok = tok.strip("\"'")
            # Пропускаем флаги и пустые токены
            if not tok or tok.startswith("-"):
                continue
            # Пропускаем голые числа и env-assignments (KEY=val)
            if tok.isdigit() or ("=" in tok and not tok.startswith(".")):
                continue
            targets.append((verb, _canonicalize(tok)))

    return targets


# Backward-compatible alias (используется в _check_bash ниже).
_extract_absolute_targets = _extract_write_targets


def _check_bash(cmd: str, root: Path) -> tuple[str, str] | None:
    """Return (verb, target) of first violation, or None."""
    targets = _extract_absolute_targets(cmd)
    for verb, target in targets:
        if not _path_is_allowed(target, root):
            return (verb, target)
    return None


def main() -> None:
    event = read_event()
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})

    root = _project_root()

    violation: tuple[str, str] | None = None
    cmd_or_target = ""

    if tool_name in {"Edit", "Write", "NotebookEdit"}:
        target = file_path(tool_input)
        if not target:
            # MultiEdit / NotebookEdit могут хранить путь в notebook_path
            target = str(tool_input.get("notebook_path", ""))
        cmd_or_target = target
        if target and not _path_is_allowed(target, root):
            violation = (tool_name, target)
    elif tool_name == "apply_patch":
        cmd_or_target = bash_command(tool_input)  # whole DSL string for bypass marker scan
        for path in apply_patch_targets(tool_input):
            if not _path_is_allowed(path, root):
                violation = ("apply_patch", path)
                break
    elif tool_name == "Bash":
        cmd = bash_command(tool_input)
        cmd_or_target = cmd
        if cmd:
            violation = _check_bash(cmd, root)
    else:
        allow()

    if not violation:
        allow()

    verb, target = violation

    if bypass("workdir", cmd_or_target, env_name="CLAUDE_ALLOW_WORKDIR"):
        log("WARN", "block_workdir", "bypass", verb, target)
        allow()

    log("BLOCK", "block_workdir", "deny", verb, target)
    block(
        f"Запись вне корня проекта заблокирована: {verb} -> {target}\n"
        f"Корень проекта: {root}\n"
        "\n"
        "Агент пилотного шаблона должен писать только внутри репозитория\n"
        "(и в общеизвестные tmp-локации: /tmp, /var/tmp, /var/folders).\n"
        "Запись в /etc, /usr, /Users/.../другой_проект и т.п. почти всегда\n"
        "означает, что агент потерялся.\n"
        "\n"
        "Что делать:\n"
        "  - проверь, действительно ли нужен абсолютный путь (часто можно\n"
        "    обойтись относительным от корня репо);\n"
        "  - worktree фичи создавай через `make wt-new` — он кладёт их в\n"
        "    .worktrees/ внутри репо, куда писать разрешено;\n"
        "  - если файл правда нужен снаружи корня — остановись и спроси\n"
        "    оунера (что и зачем); сам хук не обходи.\n"
        "\n"
        "Read-операции (cat, ls, which, find без -delete) этим хуком НЕ\n"
        "блокируются — только write."
    )


if __name__ == "__main__":
    main()
