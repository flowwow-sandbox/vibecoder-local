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

# ── Forge-CLI (gh / gt) здесь НЕ устанавливается и НЕ логинится ──────────────
# Этот скрипт идёт ДО клонирования проекта: платформа неизвестна, поэтому
# default forge нет. Bootstrap намеренно forge-neutral — только общие утилиты;
# CLI и авторизацию выбирает уже клон (make setup и ./infra/start.sh по
# эффективному origin через infra/_forge.sh) — без сканирования чужих папок.

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

echo "Готово ✓  Рабочая папка: ~/code/"
echo
echo "Дальше: клонируй свой проект в ~/code, открой папку проекта и запусти:"
echo "  make setup         # покажет инструкции установки forge-CLI по origin:"
echo "                     # gh для GitHub; gt для Gitea — вручную:"
echo "                     # https://gitea.com/gitea/cli/releases"
echo "                     # Выполни их до ./infra/start.sh"
echo "  ./infra/start.sh   # проверит auth своей forge и завершит onboarding"
echo
echo "Авторизация — после клона, своей командой: gh auth login (GitHub)"
echo "или gt auth login --host https://git.flowwow.co (Gitea)."
