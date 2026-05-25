#!/usr/bin/env bash
# bootstrap-wsl.sh — одной командой готовит WSL/Ubuntu окружение пилотника flowwow.
# Запуск (Windows-трек экрана «Прежде чем начать»): curl -fsSL <URL> | bash
# Идемпотентно: повторный запуск безопасен.
set -euo pipefail

# Версия gitleaks; поменяй при выходе нового релиза (https://github.com/gitleaks/gitleaks/releases)
GITLEAKS_VERSION="8.21.2"

if [ "$(uname -s)" != "Linux" ]; then
  echo "Этот скрипт запускается внутри WSL (Ubuntu), не на $(uname -s)." >&2
  echo "Открой приложение «Ubuntu» и запусти команду там." >&2
  exit 1
fi

# Рабочая директория проектов (единый вид с macOS: ~/code/)
mkdir -p "$HOME/code"

# ── jq и envsubst (gettext-base) ─────────────────────────────────────────────
if ! command -v jq >/dev/null 2>&1 || ! command -v envsubst >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y jq gettext-base
fi

# ── GitHub CLI (gh) ───────────────────────────────────────────────────────────
if ! command -v gh >/dev/null 2>&1; then
  sudo mkdir -p -m 755 /etc/apt/keyrings
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
  sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
  sudo apt-get update -y
  sudo apt-get install -y gh
fi

# ── gitleaks — устанавливается из release-бинаря, а не из apt ────────────────
# Пакет gitleaks отсутствует в стандартных Ubuntu-репозиториях.
if ! command -v gitleaks >/dev/null 2>&1; then
  _raw_arch="$(dpkg --print-architecture)"
  case "$_raw_arch" in
    amd64)  _gl_arch="x64"   ;;
    arm64)  _gl_arch="arm64" ;;
    *)
      echo "Ошибка: архитектура '$_raw_arch' не поддерживается — скачай gitleaks вручную:" >&2
      echo "  https://github.com/gitleaks/gitleaks/releases/tag/v${GITLEAKS_VERSION}" >&2
      exit 1
      ;;
  esac
  _gl_tmp="$(mktemp -d)"
  trap 'rm -rf "$_gl_tmp"' EXIT
  curl -fsSL \
    "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_${_gl_arch}.tar.gz" \
    -o "$_gl_tmp/gitleaks.tar.gz"
  tar -xzf "$_gl_tmp/gitleaks.tar.gz" -C "$_gl_tmp" gitleaks
  sudo install -m 0755 "$_gl_tmp/gitleaks" /usr/local/bin/gitleaks
  rm -rf "$_gl_tmp"
  trap - EXIT
fi

# ── Авторизация в GitHub ──────────────────────────────────────────────────────
if gh auth status >/dev/null 2>&1; then
  echo "gh уже авторизован ✓"
elif { : </dev/tty; } 2>/dev/null; then
  echo "Сейчас откроется авторизация GitHub. Следуй инструкции в браузере."
  gh auth login </dev/tty
else
  echo "Последний шаг — выполни в терминале:  gh auth login"
fi

echo "Готово ✓  Рабочая папка: ~/code/  Дальше — открой свой проект в Codex."
