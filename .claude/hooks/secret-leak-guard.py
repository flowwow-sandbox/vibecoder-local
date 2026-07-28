#!/usr/bin/env python3
"""PreToolUse: prevent reading or exposing secret files.

Blocks Read/Edit/Write on .env, *.key, *.pem, ~/.ssh/id_*, ~/.secrets/*.
Blocks Bash reads (cat/less/head/tail/grep) on same paths.
Bypass: CLAUDE_ALLOW_SECRETS=1.
"""
from __future__ import annotations

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
    for tok in tokens:
        tok = tok.strip("\"'")
        if not tok or tok.startswith("-"):
            continue
        hit = path_is_secret(tok)
        if hit:
            # Only block if the command seems to read/print, not edit via protected editor
            if BASH_READ_VERBS.search(cmd) or "echo" in cmd.lower() or "printenv" in cmd.lower():
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
