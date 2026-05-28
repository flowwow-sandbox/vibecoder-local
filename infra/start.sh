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
  local repo_root
  if ! repo_root=$(git rev-parse --show-toplevel 2>/dev/null); then
    echo "⚠️  .git не найден — пропускаю установку pre-commit hook"
    return 0
  fi
  local hook_path="$repo_root/.git/hooks/pre-commit"
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

# Проверяет, что имя GitHub-репо совпадает с SANDBOX_SLUG из .env.
# Если SANDBOX_SLUG не задан или gh repo view не отвечает — печатает warning и
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

  local actual_repo_name
  actual_repo_name=$(gh repo view --json name -q .name 2>/dev/null || echo "")

  if [[ -z "$actual_repo_name" ]]; then
    echo "⚠️  Не удалось получить имя репо через gh repo view (репо ещё не создан?)."
    echo "   Проверка repo name = slug пропущена — запусти ./infra/start.sh снова после первого push'а."
    return 0
  fi

  if [[ "$actual_repo_name" != "$expected_slug" ]]; then
    echo ""
    echo "❌ Имя репо не совпадает со slug."
    echo "   Текущее имя: $actual_repo_name"
    echo "   Ожидается:   $expected_slug"
    echo "   Переименуй репо: gh repo rename $expected_slug"
    echo "   (или поправь SANDBOX_SLUG в .env если slug изменился)"
    echo ""
    return 1
  fi

  echo "✓ Имя репо = slug ($expected_slug)"
  return 0
}

# --- early exit: --check-slug-only (для отладки и bats-тестов) ---
if [[ "${1:-}" == "--check-slug-only" ]]; then
  check_slug
  exit $?
fi

# --- early exit: --env-only и --hook-only работают БЕЗ deps/auth checks ---
# (пользователь может отлаживать эти шаги пока разбирается с gh login)
if [[ "${1:-}" == "--env-only" ]]; then
  setup_env
  exit 0
fi

if [[ "${1:-}" == "--hook-only" ]]; then
  setup_hook
  exit 0
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

if ! command -v gh >/dev/null 2>&1; then
  human_err "Не установлен gh CLI." "   На macOS: brew install gh"$'\n'"   На Linux: см. https://cli.github.com/"
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

# --- gh auth check ---
CHECK_AUTH_ONLY=false
if [[ "${1:-}" == "--check-auth-only" ]]; then
  CHECK_AUTH_ONLY=true
fi

if ! gh auth token >/dev/null 2>&1; then
  human_err "gh CLI не авторизован." "   Запусти: gh auth login"
fi
# Наличие токена ≠ его валидность. Провалидируем (истёк / отозван / не те
# scopes) через gh auth status, но ТОЛЬКО когда сеть доступна: gh auth status
# ходит в API и оффлайн ложно падает. При CODEX_SANDBOX_NETWORK_DISABLED=1
# (агент-песочница без сети) пропускаем, чтобы не путать «нет сети» с «токен плохой».
if [[ "${CODEX_SANDBOX_NETWORK_DISABLED:-}" != "1" ]] && ! gh auth status >/dev/null 2>&1; then
  human_err "Токен GitHub есть, но не прошёл проверку — возможно истёк/отозван или нет связи с GitHub." \
    "   Переавторизуйся: gh auth login   (если дело в сети — проверь подключение / включи Full Access в Codex)"
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
