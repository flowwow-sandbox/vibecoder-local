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
# Подстановки, escape-последовательности, heredoc и склейка кавычек не входят:
# если разбор неоднозначен, оставляем исходный текст для прежнего детектора.
_SHELL_TOKEN_RE = re.compile(
    r"[ \t]+|(?P<separator>\n|&&|\|\||[;|&])|(?P<comment>#[^\n]*)|"
    r"(?P<word>'[^']*'|\"[^\"\\$`]*\"|[\w./:=,@%+-]+)"
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
    elif tool_name == "Grep":
        # Grep takes a path; both path and pattern can touch secrets
        gpath = str(tool_input.get("path", ""))
        target = gpath
        hit = path_is_secret(gpath)

    if not hit:
        allow()

    if bypass("secrets", target):
        allow()

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
