#!/usr/bin/env bash
set -euo pipefail

# vibecoder start.sh — одноразовая инициализация после клонирования.
# Проверяет окружение, готовит .env, ставит pre-commit hook.
# Idempotent — можно запускать многократно.

# --- Human-friendly error helper ---
# Печатает сообщение об ошибке + inline action (что конкретно сделать),
# а в конце универсальный escalation-tail.
human_err() {
  local msg="$1"
  local action="$2"
  echo ""
  echo "❌ $msg"
  echo "$action"
  echo ""
  echo "Если что-то идёт не так — открой Claude Code или Codex"
  echo "и попроси агента разобраться, либо https://sandbox.flowwow.co/learn"
  echo ""
  exit 1
}

# --- OS check ---
case "${OSTYPE:-$(uname -s)}" in
  darwin*|Darwin*)
    OS=macOS
    ;;
  linux-gnu*|Linux*)
    OS=Linux
    ;;
  msys*|cygwin*|win32*|MINGW*)
    human_err "Похоже, скрипт запущен в нативном Windows (Git Bash / PowerShell)." \
      "   На Windows пилот работает внутри WSL2 (Ubuntu) — там окружение = Linux и скрипт работает.
   Установи WSL2 (PowerShell от администратора → wsl --install → перезагрузка), открой Ubuntu
   и запусти ./infra/start.sh оттуда. Подробнее — docs/runbooks/troubleshooting.md (раздел про Windows)."
    ;;
  *)
    human_err "Неизвестная ОС: ${OSTYPE:-$(uname -s)}." "   На пилоте поддержаны macOS и Linux (best-effort)."
    ;;
esac

# --- parse flags ---
REMAINING_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --check-os-only|--check-deps-only|--check-auth-only|--env-only|--hook-only|--check-slug-only)
      REMAINING_ARGS+=("$arg")
      ;;
    --*)
      echo "❌ Неизвестный флаг: $arg"
      echo "   Допустимые флаги (для отладки/тестов): --check-os-only, --check-deps-only, --check-auth-only, --env-only, --hook-only, --check-slug-only"
      echo "   Без флагов — полная инициализация."
      exit 2
      ;;
    *)
      # позиционные аргументы пропускаем (игнорируются скриптом)
      ;;
  esac
done
set -- "${REMAINING_ARGS[@]+"${REMAINING_ARGS[@]}"}"

# --- early exit для тестов ---
if [[ "${1:-}" == "--check-os-only" ]]; then
  exit 0
fi

# --- helpers: setup_env / setup_hook ---
# Эти функции вынесены, чтобы --env-only и --hook-only могли работать
# БЕЗ предварительной проверки gh auth (отладка step-by-step).
setup_env() {
  if [[ -f .env ]]; then
    # Audit: ужесточаем права если .env остался с слабыми perms.
    local current_mode
    current_mode=$(stat -c %a .env 2>/dev/null || stat -f %A .env 2>/dev/null || echo "")
    if [[ "$current_mode" != "600" ]]; then
      chmod 600 .env
      echo "✓ .env уже существует — права ужесточены до 600 (было $current_mode)"
    else
      echo "✓ .env уже существует — оставляю как есть"
    fi
    return 0
  fi

  if [[ ! -f .env.example ]]; then
    echo "⚠️  .env не найден и .env.example тоже — пропускаю шаг (необычное состояние template'а)"
    return 0
  fi

  echo ""
  echo "🔑 .env не найден — это твой файл секретов, его нужно создать вручную."
  echo ""
  echo "   В репо есть .env.example — переименуй его в .env. Это будет ТВОЙ"
  echo "   файл секретов: сюда же ты будешь складывать ключи API в будущем."
  echo ""
  echo "   Как переименовать:"
  echo "     • В VS Code / редакторе IDE: правый клик на .env.example → Rename → .env"
  echo "     • В Finder: файлы, начинающиеся с точки, по умолчанию скрыты —"
  echo "       сначала нажми Cmd+Shift+. (точка), чтобы показать их, потом"
  echo "       правый клик на .env.example → Переименовать → .env"
  echo "     • В терминале: mv .env.example .env"
  echo ""
  echo "   Потом запусти ./infra/start.sh снова."
  echo ""
  exit 1
}

# Устанавливает pre-commit hook с проверкой gitleaks.
# Тело hook'а: set -euo pipefail + проверка существования gitleaks (exit 127 vs.
# реальная находка секрета — раньше hook путал эти случаи).
setup_hook() {
  local hooks_dir
  if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
    echo "⚠️  .git не найден — пропускаю установку pre-commit hook"
    return 0
  fi
  # git rev-parse --git-path hooks, а НЕ наивная склейка "$repo_root/.git/hooks":
  # в git-worktree `.git` — ФАЙЛ (gitdir: <путь к .git/worktrees/<name>>), не
  # каталог, и склейка даёт "…/.git/hooks/pre-commit: Not a directory" под
  # set -euo pipefail — сырую ошибку bash вместо штатного сообщения. Каждый
  # свежий feature-worktree пилота (AGENTS.md, инвариант №6) — именно этот
  # случай. --git-path резолвит РЕАЛЬНЫЙ (общий для всех worktree одного репо)
  # каталог hooks корректно в обоих случаях.
  hooks_dir="$(git rev-parse --git-path hooks 2>/dev/null)" || hooks_dir=""
  if [[ -z "$hooks_dir" || ! -d "$hooks_dir" ]]; then
    echo "⚠️  Не нашёл каталог git hooks — пропускаю установку pre-commit hook"
    return 0
  fi
  local hook_path="$hooks_dir/pre-commit"
  if [[ -f "$hook_path" ]]; then
    echo "✓ pre-commit hook уже существует — оставляю как есть"
    return 0
  fi
  cat > "$hook_path" <<'HOOK_EOF'
#!/usr/bin/env bash
set -euo pipefail

if ! command -v gitleaks >/dev/null 2>&1; then
  echo "❌ gitleaks не установлен — pre-commit hook не может проверить секреты."
  echo "   Установи: brew install gitleaks (или эквивалент для твоей ОС)."
  echo "   Без gitleaks commit не разрешён — обход через --no-verify запрещён safety rules."
  exit 1
fi

gitleaks protect --staged --redact || {
  echo "❌ gitleaks обнаружил потенциальный секрет в staged изменениях."
  echo "   Если это false positive — добавь в .gitleaks.toml allowlist."
  echo "   НЕ обходи через --no-verify."
  exit 1
}
HOOK_EOF
  chmod +x "$hook_path"
  echo "✓ Установлен pre-commit hook (gitleaks)"
}

# Форма имени GitHub-репо: буквы/цифры/точка/дефис/подчёркивание. Тело HTTP-ошибки
# (фигурные скобки, кавычки, двоеточия, пробелы) под неё не подходит.
is_repo_name() {
  [[ "$1" =~ ^[A-Za-z0-9._-]+$ ]]
}

# --- early exit: --env-only и --hook-only работают БЕЗ deps/auth checks и БЕЗ
# forge detection: чисто локальные шаги (переименование .env, gitleaks hook) не
# должны внезапно требовать ни CLI, ни распознанный origin, если прежде не
# требовали (пользователь может отлаживать их до разбора с git remote).
if [[ "${1:-}" == "--env-only" ]]; then
  setup_env
  exit 0
fi

if [[ "${1:-}" == "--hook-only" ]]; then
  setup_hook
  exit 0
fi

# --- forge: определение платформы по эффективному origin (infra/_forge.sh) ---
# Root и helper берутся по расположению самого скрипта, не по cwd: start.sh,
# запущенный из подпапки или чужого каталога, не должен определить соседний
# репозиторий; .env и hook ниже работают от корня проекта.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_forge.sh"
cd "$PROJECT_ROOT"
if ! forge_detect "$PROJECT_ROOT"; then
  human_err "Не удалось определить платформу по origin этого репозитория." \
    "   origin должен указывать на github.com (https://github.com/OWNER/REPO или git@github.com:OWNER/REPO)
   или на Gitea git.flowwow.co (https://git.flowwow.co/OWNER/REPO или git@git.flowwow.co:OWNER/REPO).
   Если репозиторий ещё не склонирован — сначала склонируй его (git clone), потом запусти ./infra/start.sh из клона."
fi

# --- gt (Gitea): безопасные auth/repo-read вызовы ───────────────────────────
# Хост и repo всегда явные: --host перекрывает default_host из конфига gt,
# -R — git remote из конфига (runbook forge-cli, gt 1.2.0).
GITEA_HOST="https://git.flowwow.co"

# gt auth status --json выходит 0 при любом исходе — решают поля, а не код
# возврата: только АКТИВНАЯ (active), ПРОВЕРЕННАЯ СЕТЕВЫМ СВЕРИТЕЛЕМ (--verify →
# verified=true) credential БЕЗ ошибки, и host в точности наш инстанс. Иначе
# credential чужого инстанса из массива аккаунтов выдавал бы себя за рабочий
# (схема полей — локальная справка gt 1.2.0; живой формат ответа
# git.flowwow.co не проверялся, поэтому парсер терпит объект и массив и на
# любой неизвестной форме отказывает, не считая её успехом).
# Host принимается ровно как git.flowwow.co, https://git.flowwow.co или
# https://git.flowwow.co/ — никакого suffix/substring-матча (он пропустил бы
# evil-git.flowwow.co и подобное). gt auth token не вызывается: печатает токен.
#
# Три исхода, как и у gh-пути: 0 — credential подтверждён сетью; 1 — учётки нет
# (login — верный следующий шаг); 2 — credential сохранён, но сверитель не
# подтвердил (сеть / сбой инстанса / проверка не прошла) — НЕ повод утверждать
# «не авторизован» и заставлять перелогин. Это диагностика, не state machine:
# решение по полям то же самое, меняется только текст.
gt_auth_state() {
  local out
  out="$(gt auth status --json --verify --host "$GITEA_HOST" 2>/dev/null)" || true
  [[ -n "$out" ]] || return 1
  if printf '%s' "$out" | jq -e '[if type == "array" then .[] else . end]
    | any(.[];
        type == "object"
        and .active == true
        and .credential_available == true
        and .verified == true
        and ((.error // "") == "")
        and (.host | type == "string")
        and ((.host == "git.flowwow.co") or (.host == "https://git.flowwow.co") or (.host == "https://git.flowwow.co/")))' >/dev/null 2>&1; then
    return 0
  fi
  # Credential есть у нашего точно того же host, но подтверждения нет.
  printf '%s' "$out" | jq -e '[if type == "array" then .[] else . end]
    | any(.[];
        type == "object"
        and .credential_available == true
        and (.host | type == "string")
        and ((.host == "git.flowwow.co") or (.host == "https://git.flowwow.co") or (.host == "https://git.flowwow.co/")))' >/dev/null 2>&1 || return 1
  return 2
}

# Проверяет, что имя репозитория своей forge (по origin) совпадает с SANDBOX_SLUG из .env.
# Если SANDBOX_SLUG не задан или repo view выбранного CLI не отвечает — печатает warning и
# возвращает 0 (не блокер первого запуска start.sh до создания репо).
# Если задан и не совпадает — печатает инструкцию и возвращает non-zero.
check_slug() {
  local expected_slug=""
  if [[ -f .env ]]; then
    expected_slug=$(grep -E '^SANDBOX_SLUG=' .env | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
  fi

  if [[ -z "$expected_slug" ]]; then
    echo "⚠️  SANDBOX_SLUG не задан в .env — пропускаю проверку repo name = slug."
    echo "   Допиши SANDBOX_SLUG=<slug-из-welcome-email> в .env при следующем запуске."
    return 0
  fi

  if [[ "$FORGE_PROVIDER" == "gitea" ]]; then
    # Имя репо берём из origin (repo identity — forge_detect), доступность
    # подтверждаем безопасным чтением repo view. Probe на запись не нужен:
    # уровень permission gt CLI не отдаёт (runbook forge-cli, gt 1.2.0).
    local origin_name="${FORGE_REPO##*/}"
    if ! gt repo view --json name -R "$FORGE_REPO" --host "$GITEA_HOST" >/dev/null 2>&1; then
      echo "⚠️  Не удалось прочитать репо через gt repo view — проверка repo name = slug пропущена."
      echo "   Проверь gt auth status и доступ к ${FORGE_REPO} на git.flowwow.co."
      return 0
    fi
    if [[ "$origin_name" != "$expected_slug" ]]; then
      echo ""
      echo "❌ Имя репо не совпадает со slug."
      echo "   Текущее имя: $origin_name"
      echo "   Ожидается:   $expected_slug"
      echo "   Переименуй репо: gt repo rename $expected_slug -R $FORGE_REPO --host $GITEA_HOST"
      echo "   (или Settings репозитория на git.flowwow.co;"
      echo "    либо поправь SANDBOX_SLUG в .env если slug изменился)"
      echo ""
      return 1
    fi
    echo "✓ Имя репо = slug ($expected_slug)"
    return 0
  fi

  # `gh repo view -q` на HTTP-ошибке НЕ применяет фильтр: он копирует СЫРОЕ тело ответа
  # в stdout и выходит ≠0, а `2>/dev/null` глушит лишь stderr. Поэтому непустой ответ ещё
  # не значит «это имя репо» — без проверки формы пилоту предлагалось переименовать
  # репозиторий в JSON (`gh repo rename {"message":"Requires authentication",…}`).
  # Repo адресован явно по origin (ПОЗИЦИОННЫЙ github.com/OWNER/REPO): не по
  # default upstream/CLI config — GH_REPO/GH_HOST могли бы указать на чужой репо.
  # Не `-R`: у `gh repo view` такого флага нет (локальная справка gh 2.96.0) —
  # с ним команда падала бы, и проверка slug молча пропускалась.
  local actual_repo_name rc=0
  actual_repo_name=$(gh repo view "github.com/${FORGE_REPO}" --json name -q .name 2>/dev/null) || rc=$?

  if [[ "$rc" -ne 0 ]] || ! is_repo_name "$actual_repo_name"; then
    if [[ -z "$actual_repo_name" ]]; then
      echo "⚠️  Не удалось получить имя репо через gh repo view (репо ещё не создан?)."
      echo "   Проверка repo name = slug пропущена — запусти ./infra/start.sh снова после первого push'а."
    else
      echo "⚠️  GitHub ответил на запрос имени репо неожиданно — проверка repo name = slug пропущена."
      echo "   Обычно это транзиентный сбой gh: запусти ./infra/start.sh ещё раз, скрипт идемпотентен."
      echo "   Если повторяется — проверь gh auth status."
    fi
    return 0
  fi

  if [[ "$actual_repo_name" != "$expected_slug" ]]; then
    echo ""
    echo "❌ Имя репо не совпадает со slug."
    echo "   Текущее имя: $actual_repo_name"
    echo "   Ожидается:   $expected_slug"
    echo "   Переименуй репо: gh repo rename -R github.com/${FORGE_REPO} $expected_slug"
    echo "   (или поправь SANDBOX_SLUG в .env если slug изменился)"
    echo ""
    return 1
  fi

  echo "✓ Имя репо = slug ($expected_slug)"
  return 0
}

# --- early exit: --check-slug-only (для отладки и bats-тестов); требует
# forge detection выше — сравнение имени репо идёт с origin-идентичностью ---
if [[ "${1:-}" == "--check-slug-only" ]]; then
  check_slug
  exit $?
fi

# --- early exit для тестов проверок зависимостей ---
CHECK_DEPS_ONLY=false
if [[ "${1:-}" == "--check-deps-only" ]]; then
  CHECK_DEPS_ONLY=true
fi

# --- dependency check ---
check_dep() {
  local name="$1"
  local install_hint="$2"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "❌ Не найден: $name"
    echo "   Установить: $install_hint"
    return 1
  fi
}

DEPS_OK=true

# CLI ровно один — по выбранной forge (FORGE_CLI из detector): оба не требуются.
if [[ "$FORGE_PROVIDER" == "gitea" ]]; then
  if ! command -v gt >/dev/null 2>&1; then
    human_err "Не установлен gt CLI (Gitea)." \
      "   Установи по официальной инструкции: https://gitea.com/gitea/cli/releases"$'\n'"   Проверенных brew/apt-пакетов нет — ставь вручную из официальных релизов."
  fi
  # jq нужен для чтения gt auth status --json (решает credential_available).
  check_dep jq "brew install jq" || DEPS_OK=false
else
  if ! command -v gh >/dev/null 2>&1; then
    human_err "Не установлен gh CLI." "   На macOS: brew install gh"$'\n'"   На Linux: см. https://cli.github.com/"
  fi
fi

if ! command -v gitleaks >/dev/null 2>&1; then
  human_err "Не установлен gitleaks (нужен для pre-commit hook защиты от секретов)." "   На macOS: brew install gitleaks"$'\n'"   На Linux: см. https://github.com/gitleaks/gitleaks#installing"
fi

if [[ "$DEPS_OK" == false ]]; then
  echo ""
  echo "Установи отсутствующие зависимости и запусти снова."
  exit 1
fi

if [[ "$CHECK_DEPS_ONLY" == true ]]; then
  exit 0
fi

# --- auth check выбранного CLI ---
CHECK_AUTH_ONLY=false
if [[ "${1:-}" == "--check-auth-only" ]]; then
  CHECK_AUTH_ONLY=true
fi

if [[ "$FORGE_PROVIDER" == "gitea" ]]; then
  # Три исхода: 0 — ок; 1 — учётки нет; 2 — credential есть, но сеть/сверитель
  # не подтвердил. Второй исход не выдаём за первый: «запусти login» на рабочем
  # токене за сломанным прокси — ложный диагноз.
  gt_auth_rc=0
  gt_auth_state || gt_auth_rc=$?
  if [[ "$gt_auth_rc" -eq 2 ]]; then
    human_err "Не удалось подтвердить авторизацию на Gitea (${GITEA_HOST})." \
      "   Сохранённая учётка есть, но сверитель не подтвердил её — чаще всего это сеть
   или недоступность инстанса. Проверь: gt auth status --verify --host ${GITEA_HOST}
   Если учётка отозвана или её нет — gt auth login --host ${GITEA_HOST}"
  elif [[ "$gt_auth_rc" -ne 0 ]]; then
    human_err "gt CLI не авторизован на ${GITEA_HOST}." \
      "   Запусти: gt auth login --host ${GITEA_HOST}"
  fi
else
if ! gh auth token --hostname github.com >/dev/null 2>&1; then
  human_err "gh CLI не авторизован." "   Запусти: gh auth login"
fi
# Проверяем активный токен на том же default host, что gh auth token и
# остальные gh api: gh auth status проверяет и посторонние аккаунты/хосты.
# Наличие токена ≠ успешный API-вызов; маркер sandbox не заменяет проверку.
# Хост явный (--hostname github.com): GH_HOST действует лишь когда hostname
# не выводится из repo, а origin может быть ssh на другого host.
if ! gh api user --silent --hostname github.com >/dev/null 2>&1; then
  human_err "Токен GitHub есть, но gh api user не прошёл проверку — проблема авторизации или связи с GitHub." \
    "   Проверь сеть и доступ к GitHub. В Codex запроси сетевое разрешение для исходной команды запуска $0 целиком (аргументы: ${*:-без аргументов}), затем повтори именно эту команду.
   Отдельная проверка gh api user --silent служит диагностикой; её разрешение не распространяется на запуск скрипта.
   Если диагностика указывает на проблему токена — запусти gh auth login."
fi
fi

if [[ "$CHECK_AUTH_ONLY" == true ]]; then
  exit 0
fi

# --- .env setup ---
setup_env

# --- pre-commit hook (gitleaks) ---
setup_hook

# --- slug check (repo name = slug) ---
if ! check_slug; then
  exit 1
fi

echo "✓ ОС: $OS"

# --- next steps ---
cat <<'EOF'

──────────────────────────────────────────
✓ Инициализация завершена.

Следующие шаги:
  1. Открой Claude Code или Codex в этой папке и скажи: «запусти онбординг» — агент проведёт по остальным шагам.
──────────────────────────────────────────
EOF
