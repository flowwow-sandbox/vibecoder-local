#!/usr/bin/env python3
"""PreToolUse: prevent reading or exposing secret files.

Blocks Read/Edit/Write on .env, *.key, *.pem, ~/.ssh/id_*, ~/.secrets/*.
Blocks Bash reads (cat/less/head/tail/grep) on same paths.
Bypass: CLAUDE_ALLOW_SECRETS=1.
"""
from __future__ import annotations

import ast
import re
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
    read_event,
)

SECRET_PATH_REGEX = re.compile(
    r"(?:^|/|\\)("
    r"\.env(?:\.[a-z0-9]+)?"          # .env, .env.local, .env.production
    r"|\.envrc"
    r"|[^/\\]*\.key"                    # *.key (file tail)
    r"|[^/\\]*\.pem"                    # *.pem
    r"|id_(?:rsa|ed25519|ecdsa|dsa)(?:\.pub)?"  # ssh keys
    r"|credentials(?:\.json)?"
    r"|secrets?\.(?:json|yaml|yml|toml)"
    r")(?:$|/|\\)",
    re.IGNORECASE,
)

# Local modification (vibecoder pilot): explicit allowlist for
# placeholder env files. SECRET_PATH_REGEX otherwise matches `.env.example`
# (and `.env.sample`, `.env.template`) because the suffix subgroup
# `\.[a-z0-9]+` is non-discriminating. These files are part of the repo
# template — pilot must be able to read/copy them. Extending allowlist
# here keeps the upstream regex byte-identical (easier to reconcile on
# next AnastasiyaW pull).
SAFE_PLACEHOLDER_BASENAMES = {
    ".env.example",
    ".env.sample",
    ".env.template",
}

SECRET_DIR_REGEX = re.compile(
    r"(?:^|/|\\)(\.secrets?|\.aws|\.ssh)(?:$|/|\\)",
    re.IGNORECASE,
)

# jq/yq читают файл целиком и печатают его — для `.env` это ровно та же утечка,
# что и `cat`, но их в списке не было.
BASH_READ_VERBS = re.compile(
    r"\b(cat|less|more|head|tail|grep|rg|ripgrep|bat|xxd|hexdump|jq|yq|source|\.)\s+\S",
    re.IGNORECASE,
)

# Консервативный поднабор shell: литеральные слова/кавычки и разделители.
# Подстановки ($, `) и склейка кавычек не входят: где разбор неоднозначен,
# bash_verb_text оставляет исходный текст, _shell_word_segments пропускает
# только свой сегмент. Escape внутри двойных кавычек входит в разбор.
_SHELL_TOKEN_RE = re.compile(
    r"[ \t]+|(?P<separator>\n|&&|\|\||[;|&])|(?P<comment>#[^\n]*)|"
    r"(?P<word>'[^']*'|\"(?:[^\"\\$`]|\\.)*\"|[\w./:=,@%+-]+)"
)

# Known uv run option arities. Unknown options and modes that reinterpret the
# command (--module/--script) do not qualify for the Python-code exception.
# --python/-p can select an arbitrary executable, so they are excluded too.
_UV_RUN_FLAGS = frozenset(
    ("--active --all-extras --all-groups --all-packages --no-dev --only-dev "
     "--no-default-groups --no-editable --exact --no-env-file --isolated "
     "--no-sync --locked --frozen --no-project --no-index --no-sources "
     "--reinstall --compile-bytecode --no-build-isolation --no-build --no-binary "
     "--no-cache -n --refresh --upgrade -U --managed-python --no-managed-python "
     "--no-python-downloads --quiet -q --verbose -v --system-certs --offline "
     "--no-progress --no-config").split()
)
_UV_RUN_VALUE_OPTIONS = frozenset(
    ("--env-file --extra --no-extra --group --no-group --only-group "
     "--no-editable-package --with -w --with-editable --with-requirements "
     "--package --python-platform --index --default-index --index-url -i "
     "--extra-index-url --find-links -f --index-strategy --keyring-provider "
     "--upgrade-package -P --upgrade-group --resolution --prerelease "
     "--fork-strategy --exclude-newer --exclude-newer-package --no-sources-package "
     "--reinstall-package --link-mode --config-setting -C --config-settings-package "
     "--no-build-isolation-package --no-build-package --no-binary-package "
     "--cache-dir --refresh-package --color --allow-insecure-host "
     "--directory --project --config-file").split()
)


def mask_python_imports(code: str) -> str:
    """Mask AST imports only; strings containing shell commands stay visible."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError):
        return code
    # AST columns are UTF-8 byte offsets, including for non-ASCII source.
    raw = code.encode("utf-8")
    line_starts = [0]
    for line in raw.splitlines(keepends=True):
        line_starts.append(line_starts[-1] + len(line))
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            start = line_starts[node.lineno - 1] + node.col_offset
            end = line_starts[node.end_lineno - 1] + node.end_col_offset
            spans.append((start, end))
    for start, end in sorted(spans, reverse=True):
        raw = raw[:start] + b" " * (end - start) + raw[end:]
    return raw.decode("utf-8")


def python_code_argument(words: list[re.Match[str]]) -> re.Match[str] | None:
    """Recognize unqualified python -c or uv run [known options] python -c."""
    values = [m.group()[1:-1] if m.group().startswith(("'", '"')) else m.group() for m in words]
    if not values:
        return None
    i = 0
    if values[0] == "uv":
        if len(values) < 2 or values[1] != "run":
            return None
        i = 2
        while i < len(values):
            option, equals, value = values[i].partition("=")
            if values[i] in _UV_RUN_FLAGS or re.fullmatch(r"-[qv]+", values[i]):
                i += 1
            elif option in _UV_RUN_VALUE_OPTIONS:
                if equals:
                    if not value:
                        return None
                    i += 1
                elif i + 1 < len(values) and not values[i + 1].startswith("-"):
                    i += 2
                else:
                    return None
            else:
                break
        if i < len(values) and values[i] == "--":
            i += 1
    if (
        i + 2 < len(values)
        and re.fullmatch(r"python(?:3(?:\.\d+)*)?", values[i])
        and values[i + 1] == "-c"
        and words[i + 2].group().startswith(("'", '"'))
    ):
        return words[i + 2]
    return None


def bash_verb_text(cmd: str) -> str:
    """Exclude imports only inside a literal code argument of a Python command."""
    segments: list[list[re.Match[str]]] = [[]]
    pos = 0
    last_word_end = None
    while pos < len(cmd):
        m = _SHELL_TOKEN_RE.match(cmd, pos)
        if m is None:
            return cmd
        if m.group("comment"):
            if last_word_end == m.start():
                return cmd  # A hash inside a word is not a shell comment.
        elif m.group("separator"):
            segments.append([])
            last_word_end = None
        elif m.group("word"):
            if last_word_end == m.start():
                return cmd  # Adjacent quoted/unquoted pieces form one shell word.
            segments[-1].append(m)
            last_word_end = m.end()
        pos = m.end()
    replacements = []
    for words in segments:
        arg = python_code_argument(words)
        if arg is not None:
            code = arg.group()[1:-1]
            replacements.append((arg.start() + 1, arg.end() - 1, mask_python_imports(code)))
    for start, end, replacement in reversed(replacements):
        cmd = cmd[:start] + replacement + cmd[end:]
    return cmd


# ── gt auth token: команда печатает credential, а не читает файл ──────────────
# Path-детектор такое не видит: токен не в аргументах, а в output. Разбор — тот
# же консервативный поднабор shell (см. _SHELL_TOKEN_RE): литеральные слова,
# кавычки и разделители; неизвестный флаг — не блокируем (лучше пропуск, чем
# ложный стоп рутины вроде gt auth status), а неоднозначный сегмент (склейка
# кавычек, hash внутри слова) отключает только себя, не всю строку. Тело quoted
# heredoc — текст в stdin, не команды. Флаги — только подтверждённые
# `gt help` 1.2.0: глобальные допустимы до и после имени команды;
# --json/--csv берут необязательное поле только через `=`.
_GT_VALUE_FLAGS = frozenset(
    "--cwd --host --remote --repo -R --sudo --user --jq -q --template".split()
)
_GT_FLAG_WORDS = frozenset(
    "--debug --interactive --no-input --yes -y --json --csv".split()
)
_GT_ENV_ASSIGN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")

# Quoted heredoc не раскрывает подстановки, но получатель stdin может его исполнить.
# Пробел/таб между << и delimiter допустимы; here-string (`<<<`), escaped `<`
# и склеенный delimiter (`<<'EOF'x`) отсекаются в _strip_quoted_heredoc_bodies.
_HEREDOC_OPEN_RE = re.compile(r"<<(-?)[ \t]*(['\"])([^'\"\n]+)\2")
# Только конец ввода, shell-пробел или оператор завершают delimiter-word.
_DELIM_END_RE = re.compile(r"(?:[ \t\n;&|<>()]|$)")
# Hash внутри слова не комментарий: вместе с хвостом до пробела/разделителя/
# подстановки это одно shell-слово, разбивать его на слова нельзя.
_AMBIGUOUS_WORD_TAIL_RE = re.compile(r"[^\s;&|$`]+")


def _quoted_heredoc_body_end(cmd: str, start: int, delim: str, allow_tabs: bool) -> int | None:
    """Позиция после точной строки-разделителя; None, если граница не доказана."""
    pos = start
    while pos < len(cmd):
        nl = cmd.find("\n", pos)
        line = cmd[pos:] if nl == -1 else cmd[pos:nl]
        if (line.lstrip("\t") if allow_tabs else line) == delim:
            return len(cmd) if nl == -1 else nl + 1
        if nl == -1:
            return None
        pos = nl + 1
    return None


def _strip_quoted_heredoc_bodies(cmd: str) -> str:
    """Убрать только текст простого standalone cat с quoted heredoc.

    shortcut: только cat без аргументов/конвейера, простой quoted delimiter и строка открытия.
    При неподдержанном синтаксисе возвращаем исходный текст для консервативной
    проверки; расширять поднабор только с тестами, доказывающими границы.
    """
    out: list[str] = []
    pos = 0
    n = len(cmd)
    while pos < n:
        ch = cmd[pos]
        if ch == "\\":
            if cmd[pos + 1:pos + 2] == "\n":
                return cmd  # Продолжение логической строки не разбираем.
            out.append(cmd[pos:pos + 2])
            pos += 2
        elif ch in "$`|&();{}>":
            return cmd  # Подстановки, группы и передача вывода требуют shell-parser.
        elif ch == "'":
            end = cmd.find("'", pos + 1)
            end = n if end == -1 else end + 1
            out.append(cmd[pos:end])
            pos = end
        elif ch == '"':
            end = pos + 1
            while end < n and cmd[end] != '"':
                if cmd[end] in "$`" or cmd[end:end + 2] == "\\\n":
                    return cmd
                end += 2 if cmd[end] == "\\" else 1
            end = min(end + 1, n)
            out.append(cmd[pos:end])
            pos = end
        elif ch == "<" and cmd[pos - 1:pos] not in ("<", "\\"):
            # `<` после `<` — часть here-string `<<<`, после `\` — литеральный
            # символ: парой << они operator'а не образуют.
            m = _HEREDOC_OPEN_RE.match(cmd, pos)
            if (
                m is None
                or not _DELIM_END_RE.match(cmd, m.end())
                or (m.group(2) == '"' and "\\" in m.group(3))
            ):
                return cmd  # Не угадываем ни границы unquoted-тела, ни quote removal.
            nl = cmd.find("\n", m.end())
            if nl == -1:
                return cmd
            # Доказываем текстового получателя и отсутствие передачи stdin дальше.
            line_start = cmd.rfind("\n", 0, pos) + 1
            if cmd[line_start:pos].strip(" \t") != "cat" or cmd[m.end():nl].strip(" \t"):
                return cmd
            body_end = _quoted_heredoc_body_end(cmd, nl + 1, m.group(3), bool(m.group(1)))
            if body_end is None:
                return cmd
            out.append(cmd[pos:nl + 1])  # строка открытия целиком, с командами
            pos = body_end
            out.append("\n")  # только доказанное тело и delimiter — не команды
        elif ch == "#" and (pos == 0 or cmd[pos - 1] in " \t\n;&|("):
            nl = cmd.find("\n", pos)
            end = n if nl == -1 else nl
            out.append(cmd[pos:end])
            pos = end
        else:
            out.append(ch)
            pos += 1
    return "".join(out)


def _shell_word_segments(cmd: str) -> list[list[str]]:
    """Сегменты команды как списки слов без кавычек. Неоднозначный сегмент
    (склейка кавычек, hash внутри слова) отбрасывается, остальные проверяются."""
    segments: list[list[str] | None] = [[]]
    pos = 0
    last_word_end = None
    cmd = _strip_quoted_heredoc_bodies(cmd)
    while pos < len(cmd):
        m = _SHELL_TOKEN_RE.match(cmd, pos)
        if m is None:
            # Нераспознанный символ (>, <, $, скобки) — граница слова, как
            # разделитель: `gt auth token > f` и `echo "$(gt auth token)"`
            # всё же разбираются.
            segments.append([])
            last_word_end = None
            pos += 1
            continue
        elif m.group("comment"):
            if last_word_end == m.start():
                # hash внутри слова — сегмент неоднозначен, остальные проверяем
                segments[-1] = None
                last_word_end = None
                pos = _AMBIGUOUS_WORD_TAIL_RE.match(cmd, m.start()).end()
                continue
        elif m.group("separator"):
            segments.append([])
            last_word_end = None
        elif m.group("word"):
            if last_word_end == m.start():
                segments[-1] = None  # смежные куски кавычек — одно слово, не угадываем
            elif segments[-1] is not None:
                word = m.group()
                segments[-1].append(word[1:-1] if word[0] in "'\"" else word)
            last_word_end = m.end()
        pos = m.end()
    return [s for s in segments if s is not None]


def bash_prints_credential(cmd: str) -> bool:
    """Хоть один сегмент команды запускает `gt auth token` — печать значения
    токена Gitea в stdout, та же утечка в транскрипт, что и cat .env."""
    for words in _shell_word_segments(cmd):
        i = 0
        # Простые префиксы запуска: env [VAR=…], command, VAR=…
        while i < len(words) and (
            words[i] in ("env", "command") or _GT_ENV_ASSIGN_RE.fullmatch(words[i])
        ):
            i += 1
        if i >= len(words) or words[i].rsplit("/", 1)[-1] != "gt":
            continue
        i += 1
        help_only = False
        positionals: list[str] = []
        while i < len(words):
            word = words[i]
            if word in ("--help", "-h"):
                help_only = True  # справка, не export — позиция любая, но не значение флага
                break
            option, equals, value = word.partition("=")
            if option in _GT_FLAG_WORDS:
                i += 1
            elif option in _GT_VALUE_FLAGS:
                if equals:
                    if not value:
                        break  # `--host=` без значения — сам gt откажет
                    i += 1
                elif i + 1 < len(words):
                    i += 2
                else:
                    break
            elif re.fullmatch(r"-[Rq].+", word):
                i += 1  # слитное значение короткого value-флага: -Rowner/repo, -q.field
            elif word.startswith("-"):
                break  # неизвестный флаг: не выдумываем, не блокируем
            else:
                positionals.append(word)
                i += 1
        if not help_only and positionals[:2] == ["auth", "token"]:
            return True
    return False


def path_is_secret(path: str) -> str | None:
    if not path:
        return None
    # Local modification (vibecoder pilot): exempt explicit placeholder
    # filenames so pilot can read .env.example etc. without bypass env-var.
    basename = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if basename in SAFE_PLACEHOLDER_BASENAMES:
        return None
    m = SECRET_PATH_REGEX.search(path)
    if m:
        return m.group(1)
    m = SECRET_DIR_REGEX.search(path)
    if m:
        return m.group(1) + "/"
    return None


def bash_touches_secret(cmd: str) -> str | None:
    """Detect reads/prints of secret-like paths inside a Bash command."""
    if not cmd:
        return None
    # Split on common separators to test each token that looks path-ish.
    tokens = re.split(r"[\s;&|<>()`]+", cmd)
    # Python-импорты исключаем только из проверенного аргумента python -c.
    verb_text = bash_verb_text(cmd)
    for tok in tokens:
        tok = tok.strip("\"'")
        if not tok or tok.startswith("-"):
            continue
        hit = path_is_secret(tok)
        if hit:
            # Only block if the command seems to read/print, not edit via protected editor
            if BASH_READ_VERBS.search(verb_text) or "echo" in cmd.lower() or "printenv" in cmd.lower():
                return hit
            # Reading via redirection like `< .env` also leaks
            if re.search(r"<\s*\S*" + re.escape(tok), cmd):
                return hit
    return None


def main() -> None:
    event = read_event()
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})

    hit: str | None = None
    credential_hit = False
    target = ""

    if tool_name in {"Read", "Edit", "Write", "NotebookEdit"}:
        target = file_path(tool_input)
        hit = path_is_secret(target)
    elif tool_name == "apply_patch":
        for path in apply_patch_targets(tool_input):
            h = path_is_secret(path)
            if h:
                hit = h
                target = path
                break
    elif tool_name == "Bash":
        target = bash_command(tool_input)
        hit = bash_touches_secret(target)
        if not hit:
            credential_hit = bash_prints_credential(target)
    elif tool_name == "Grep":
        # Grep takes a path; both path and pattern can touch secrets
        gpath = str(tool_input.get("path", ""))
        target = gpath
        hit = path_is_secret(gpath)

    if not hit and not credential_hit:
        allow()

    if bypass("secrets", target):
        allow()

    if credential_hit:
        # Команда не повторяется в сообщении: её аргументы могут нести значения.
        block(
            "Команда заблокирована: `gt auth token` печатает значение токена Gitea\n"
            "в output, а транскрипт сессии — тоже лог, секрет из него не убрать.\n"
            "Безопасная проверка авторизации — поля статуса, не печать секрета:\n"
            "  gt auth status --json --verify --host https://git.flowwow.co\n"
            "(нужны точный host, active=true, credential_available=true,\n"
            "verified=true и пустой error; exit 0 недостаточен —\n"
            "docs/contracts/forge-platform.md)."
        )

    block(
        f"Secret file access blocked: {hit!r}.\n"
        "Причина: секреты (.env, ключи, ~/.ssh/id_*, ~/.secrets/*) не читать без явной\n"
        "пользовательской просьбы. Даже чтение для 'проверить' рискует утечкой в логи/контекст.\n"
        "Если действительно нужно — не обходи хук сам:\n"
        "  1) остановись и спроси оунера, что именно и зачем\n"
        "  2) если он подтвердит — не печатай содержимое секрета в output"
    )


if __name__ == "__main__":
    main()
