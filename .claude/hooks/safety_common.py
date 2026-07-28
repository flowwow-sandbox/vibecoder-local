"""Shared safety hook utilities.

Reads PreToolUse JSON from stdin, exposes helpers for verdicts and parsing.
Exit conventions:
  - exit 0 + empty stdout: allow (silent pass-through)
  - exit 0 + JSON {"decision": "block", "reason": "..."} on stdout: block
  - exit 2 + message on stderr: block with user-visible reason

See docs: https://docs.anthropic.com/en/docs/claude-code/hooks
"""
from __future__ import annotations

import json
import os
import re
import sys

# Windows default stdout is cp1252 which chokes on Cyrillic in block reasons.
# Reconfigure to utf-8 before any print. No-op on platforms that already use utf-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


def read_event() -> dict:
    """Parse PreToolUse event from stdin. Returns empty dict on failure."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return {}
        return json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return {}


# Значения, которые не должны оседать в аудит-логе в сыром виде. Тот же набор,
# что ищет api-key-leak-detector в выводе инструментов — один источник правды,
# чтобы «ловим» и «маскируем» не разъезжались.
SECRET_PATTERNS: list[tuple[str, "re.Pattern[str]"]] = [
    ("Anthropic API key", re.compile(r"sk-ant-[A-Za-z0-9\-_]{32,}")),
    # Префиксы OpenAI множатся (proj/admin/svcacct/…), а тело ключа содержит
    # base64url-пунктуацию: узкий паттерн оставлял такие ключи в логе целиком.
    ("OpenAI API key", re.compile(r"sk-(?:[a-z]+-)?[A-Za-z0-9_\-]{32,}")),
    ("GitHub PAT", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("GitHub fine-grained", re.compile(r"github_pat_[A-Za-z0-9_]{80,}")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("AWS secret key",
     re.compile(r"aws[_\-\s]*secret[_\-\s]*access[_\-\s]*key[\"'\s=:]+([A-Za-z0-9/+=]{40})",
                re.IGNORECASE)),
    ("Stripe live key", re.compile(r"\b(?:sk|rk|pk)_live_[0-9a-zA-Z]{24,}")),
    ("Stripe test key", re.compile(r"\b(?:sk|rk|pk)_test_[0-9a-zA-Z]{24,}")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    # Матчим ВЕСЬ PEM-блок, а не только маркер: иначе redact_secrets вырезает
    # строку `-----BEGIN …-----`, а base64-тело ключа остаётся в логе. Если
    # END-маркера нет (обрезанный вывод) — съедаем остаток текста: потерять
    # хвост записи дешевле, чем сохранить ключ.
    # `BLOCK` в хвосте маркера — форма ASCII-armored OpenPGP
    # («-----BEGIN PGP PRIVATE KEY BLOCK-----»).
    ("Private key block",
     re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY(?: BLOCK)?-----"
                r"(?:[\s\S]*?-----END (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?"
                r"PRIVATE KEY(?: BLOCK)?-----"
                r"|[\s\S]*)")),
    ("JWT token",
     re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")),
    # Алфавит — полный base64/base64url плюс `~`: токен со слешем или плюсом
    # в первых же символах иначе не матчился и уходил в лог целиком.
    ("Generic bearer token",
     re.compile(r"\b[Bb]earer\s+[A-Za-z0-9_\-\.=/+~]{40,}")),
]


def block(reason: str) -> None:
    """Emit a structured block verdict and exit."""
    msg = {"decision": "block", "reason": reason}
    print(json.dumps(msg, ensure_ascii=False))
    sys.exit(0)


def allow() -> None:
    """Pass-through: no output, exit 0."""
    sys.exit(0)


def bypass_env(name: str) -> bool:
    """Check CLAUDE_ALLOW_* override. Accepts 1/true/yes.

    Окружение хука — это окружение харнесса (агент-тула), а не bash-команды:
    хук запускается как sibling-процесс, поэтому inline-префикс `FOO=1 cmd`
    в команде агента хуку НЕ виден. Выставить переменную может только человек —
    в окружении, из которого запущен агент-тул. Это намеренно: единственный
    обход guard'а лежит вне досягаемости самого агента.
    """
    val = os.environ.get(name, "").strip().lower()
    return val in {"1", "true", "yes", "on"}


def bypass(name: str, command_or_content: str = "", env_name: str | None = None) -> bool:
    """Bypass-проверка. True только если человек выставил CLAUDE_ALLOW_* в окружении.

    Маркера в тексте команды (`# claude-bypass: …`) намеренно НЕ существует:
    команду пишет агент, и такой маркер позволял бы ему выписывать себе
    разрешение самому — защита становилась бы декоративной. См.
    docs/contracts/safety-rules.md §3.1.

    name: short bypass key (e.g. "injection", "destructive")
    command_or_content: не используется; параметр сохранён ради стабильной
        сигнатуры вызовов в guard'ах
    env_name: defaults to CLAUDE_ALLOW_<NAME_UPPER>
    """
    if env_name is None:
        env_name = f"CLAUDE_ALLOW_{name.upper().replace('-', '_')}"
    return bypass_env(env_name)


def bash_command(tool_input: dict) -> str:
    """Extract command string from Bash tool input."""
    return str(tool_input.get("command", ""))


def file_path(tool_input: dict) -> str:
    """Extract file path from Read/Edit/Write tool input."""
    return str(tool_input.get("file_path", ""))


# Codex's apply_patch tool packages all file ops into a single DSL string in
# tool_input.command. We parse the operation markers so guards can check each
# affected path. Source/dest для Move to оба считаем target'ами — оба пути
# физически модифицируются (source удаляется, dest создаётся).
_APPLY_PATCH_OP_RE = re.compile(
    r"^\*{3}\s*(?:Add File|Update File|Delete File|Move to)\s*:\s*(.+?)\s*$",
    re.MULTILINE,
)


def apply_patch_targets(tool_input: dict) -> list[str]:
    """Extract file paths from an apply_patch DSL command string.

    Returns deduplicated list preserving discovery order. Empty list on
    missing or unparseable input.
    """
    cmd = str(tool_input.get("command", ""))
    if not cmd:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for m in _APPLY_PATCH_OP_RE.finditer(cmd):
        path = m.group(1).strip()
        if path and path not in seen:
            seen.add(path)
            found.append(path)
    return found


def any_match(text: str, patterns: list[str]) -> str | None:
    """Return the first matching regex (string form) or None. Case-insensitive."""
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return pat
    return None


# Глобальные опции git идут ДО подкоманды (`git -C app push --force`), поэтому
# паттерны вида `git\s+push` их не видят и пропускают запрещённую операцию.
_GIT_GLOBAL_OPTS_RE = re.compile(
    r"\bgit\s+(?:"
    r"(?:-C|-c|--exec-path|--git-dir|--work-tree|--namespace|--super-prefix)"
    r"(?:=\S+|\s+\S+)"
    r"|--(?:no-pager|paginate|bare|literal-pathspecs|no-replace-objects|glob-pathspecs"
    r"|noglob-pathspecs|icase-pathspecs|no-optional-locks)"
    r"|-p"
    r")\s+",
    re.IGNORECASE,
)


def strip_git_global_opts(cmd: str) -> str:
    """Убрать глобальные опции git, чтобы подкоманда встала сразу после `git`.

    `git -C app -c user.name=x push --force` → `git push --force`. Применяется
    к копии команды перед матчингом; в лог и в сообщение пользователю идёт
    исходный текст.
    """
    previous = None
    while previous != cmd:
        previous = cmd
        cmd = _GIT_GLOBAL_OPTS_RE.sub("git ", cmd)
    return cmd


# --- Destructive SQL: только для клиентов ВНЕШНИХ БД -------------------------
# Разрешённое хранилище пилота — локальная SQLite под app/data (safety-rules §1).
# Дропнуть свою dev-таблицу или грепнуть собственную миграцию — рутина, и
# блокировать текст «DROP TABLE» в любой команде значит ломать нормальную
# работу. Катастрофичен тот же SQL, отправленный в ЧУЖУЮ БД — там нет ни
# бэкапа под рукой, ни права на ошибку. Поэтому детектор смотрит на клиента:
# psql/mysql/mongo/redis-cli/dropdb — да, sqlite3/grep/cat — нет.
EXTERNAL_DB_CLIENTS = {
    "psql", "pg_dump", "pg_restore", "dropdb", "dropuser", "createdb",
    "mysql", "mysqladmin", "mariadb",
    "mongo", "mongosh", "mongodump",
    "redis-cli",
    "clickhouse-client",
}

# Имя отношения в SQL: `orders`, `public.orders`, `"orders"`, `` `orders` ``.
_RELATION = r"[\w.\"'`\[\]]+"

DB_DESTRUCTIVE_PATTERNS = [
    r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b",
    # `TABLE` необязателен в PostgreSQL и MySQL: `TRUNCATE orders;` — валидный SQL.
    rf"\bTRUNCATE\s+(TABLE\s+)?{_RELATION}",
    # DELETE без WHERE. Ловим по ОТСУТСТВИЮ WHERE до конца оператора, а не по
    # тому, что оператор кончается сразу за именем: `DELETE FROM orders
    # RETURNING id` и `DELETE FROM orders AS o` — тот же полный снос строк.
    rf"\bDELETE\s+FROM\s+{_RELATION}(?![^;]*\bWHERE\b)",
    r"\bdropdb\b",
    r"\bdropuser\b",
    r"\bdropDatabase\b",
    r"\bflushall\b",
    r"\bflushdb\b",
    # Удаление БД подкомандой клиента, а не SQL-текстом:
    # `mysqladmin --force -h db drop production`.
    r"\bmysqladmin\b[^|;\n]*\bdrop\b",
]

# Перевод строки — такой же разделитель команд, как `;`: агент часто шлёт
# многострочный Bash, и без \n клиент со второй строки попадал бы в сегмент
# чужого verb'а (`cd app\npsql -c "DROP TABLE …"` → verb=cd → детект теряется).
_SEGMENT_SPLIT_RE = re.compile(r"(?:;|&&|\|\||\||\n)")
# Подстановки `$(…)` и backticks — используются при разборе verb'а сегмента
# (см. _segment_runs_db_client).
_SUBST_RE = re.compile(r"\$\([^()]*(?:\([^()]*\)[^()]*)*\)|`[^`]*`")
# Флаги, съедающие следующий токен, — ПЕР-обёртка: `sudo -p prompt` берёт
# аргумент, а `time -p` (portable output) нет, и общий список молча съедал
# обёрнутую команду вместе с флагом.
_WRAPPER_FLAG_ARGS = {
    "sudo": {"-u", "-g", "-p", "-C", "-r", "-t", "-U", "--user", "--group", "--prompt"},
    "env": {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"},
    "nohup": set(),
    "exec": {"-a"},
    "time": {"-f", "--format", "-o", "--output"},
}
_ENV_PREFIXES = frozenset(_WRAPPER_FLAG_ARGS)

# Обёртки, запускающие команду где-то ещё (контейнер, под, другой хост) или
# просто перед собой: сам verb здесь — docker/timeout/bash, а настоящий клиент
# стоит дальше в той же строке. Без их разбора `docker exec pg psql -c "DROP
# TABLE …"`, `timeout 5 psql …` и `bash -lc 'psql …'` проходили бы мимо.
_EXEC_WRAPPERS = {
    # запуск в другом окружении
    "docker", "podman", "nerdctl", "kubectl", "oc", "ssh",
    # локальные обёртки запуска
    "command", "timeout", "nice", "ionice", "stdbuf", "setsid", "xargs",
    "bash", "sh", "zsh", "dash",
}


# Присваивания в той же команде: `DBCLI=psql; "$DBCLI" -c "…"`. Без их учёта
# verb'ом становится сама переменная, и клиент не опознаётся.
_ASSIGN_RE = re.compile(r"(?:^|[\s;&|])([A-Za-z_][A-Za-z0-9_]*)=([^\s;&|]+)")
_VAR_REF_RE = re.compile(r"^\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?$")


def _var_bindings(cmd: str) -> dict[str, str]:
    return {m.group(1): m.group(2).strip("\"'") for m in _ASSIGN_RE.finditer(cmd)}


def segment_verb(segment: str, bindings: dict[str, str] | None = None) -> str:
    """Первое слово сегмента — команда. Пропускает sudo/env/VAR=value префиксы.

    Возвращает basename: `/usr/local/bin/psql` и `psql` — одна и та же команда.
    Здесь нормализация пути безопасна: она только помогает узнать клиента.

    `bindings` — присваивания из той же команды: `"$DBCLI"` раскрывается в
    значение. Нераскрытая переменная возвращается как есть (`$DBCLI`), чтобы
    вызывающий мог выбрать fail-closed.
    """
    tokens = segment.split()
    i = 0
    wrapper: str | None = None
    while i < len(tokens):
        # Снимаем и кавычки, и операторы группировки: `(psql -c …)` в подоболочке
        # давал verb «(psql», и клиент не опознавался.
        tok = tokens[i].strip("\"'(){}")
        if tok in _ENV_PREFIXES:
            wrapper = tok
            i += 1
            continue
        if "=" in tok and not tok.startswith(("/", "-")):  # VAR=value
            i += 1
            continue
        if wrapper and tok.startswith("-"):
            i += 2 if tok in _WRAPPER_FLAG_ARGS[wrapper] else 1
            continue
        ref = _VAR_REF_RE.match(tok)
        if ref and bindings:
            tok = bindings.get(ref.group(1), tok)
        return tok.rsplit("/", 1)[-1]
    return ""


def _segment_runs_db_client(segment: str, bindings: dict[str, str] | None = None) -> bool:
    """Клиент внешней БД запускается этим сегментом — напрямую, через exec-обёртку,
    через путь из подстановки или через переменную."""
    verb = segment_verb(segment, bindings)
    if verb in EXTERNAL_DB_CLIENTS:
        return True
    # Нераскрытая переменная в позиции команды (`"$DBCLI" -c …`, значение пришло
    # из окружения): что за бинарь — неизвестно, поэтому fail-closed. Ценой
    # редкого лишнего вопроса оунеру закрываем тривиальный обход детектора.
    if verb.startswith("$"):
        return True
    # Путь к бинарю может быть собран подстановкой:
    #   $(brew --prefix postgresql@16)/bin/psql -c "…"  → verb «$(brew»
    #   "$(command -v psql)" -c "…"                     → verb «"$(command»
    # Смотрим и на команду без подстановок, и внутрь самих подстановок.
    if segment_verb(_SUBST_RE.sub(" ", segment)) in EXTERNAL_DB_CLIENTS:
        return True
    for m in _SUBST_RE.finditer(segment):
        # Токены внутри подстановки несут её синтаксис: `$(command`, `psql)`.
        if any(
            tok.strip("\"'`()$").rsplit("/", 1)[-1] in EXTERNAL_DB_CLIENTS
            for tok in m.group(0).split()
        ):
            return True
    if verb not in _EXEC_WRAPPERS:
        return False
    # docker exec <name> psql … / kubectl exec pod -- psql … / ssh host psql …
    return any(
        tok.strip("\"'").rsplit("/", 1)[-1] in EXTERNAL_DB_CLIENTS
        for tok in segment.split()[1:]
    )


def has_external_db_client(cmd: str) -> bool:
    """True, если хоть один сегмент команды ЗАПУСКАЕТ клиент внешней БД.

    Именно запускает: `grep psql history.txt` — не считается, там psql лишь
    аргумент. Исключение — exec-обёртки (см. _segment_runs_db_client): там
    клиент стоит среди аргументов по определению.
    """
    bindings = _var_bindings(cmd)
    return any(
        _segment_runs_db_client(seg, bindings) for seg in _SEGMENT_SPLIT_RE.split(cmd)
    )


def db_destructive_hit(cmd: str) -> str | None:
    """Вернуть сработавший SQL-паттерн, если команда бьёт по ВНЕШНЕЙ БД.

    Двухшаговая проверка — сначала «есть ли вообще клиент внешней БД», потом
    поиск глагола по ВСЕЙ команде. Искать глагол внутри того же сегмента, что и
    клиент, нельзя: `;` внутри SQL-строки разделяет запросы, а не команды shell,
    так что `psql -c "BEGIN; DROP TABLE x; COMMIT"`, heredoc-пейлоад и
    `echo "DROP TABLE x" | psql` расклеивались бы на разные сегменты и проходили.

    Оборотная сторона: `psql -c "SELECT 1" && grep "DROP TABLE" old.sql` даст
    ложное срабатывание. Это осознанный fail-closed — сочетание редкое, а цена
    пропуска (дроп чужой БД) несопоставима с ценой лишнего вопроса оунеру.

    Локальный `sqlite3` и чтение (`grep`/`cat`) клиентами не считаются: см.
    комментарий к EXTERNAL_DB_CLIENTS.
    """
    if not cmd or not has_external_db_client(cmd):
        return None
    return any_match(cmd, DB_DESTRUCTIVE_PATTERNS)
