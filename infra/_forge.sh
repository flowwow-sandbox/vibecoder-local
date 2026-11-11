#!/usr/bin/env bash
# _forge.sh — определение основной forge и repo по эффективным origin URL.
# Использование: source infra/_forge.sh; forge_detect [repo_dir] (по умолчанию ".").
# Успех (return 0): выставляет FORGE_PROVIDER (github|gitea), FORGE_HOST,
# FORGE_REPO (owner/repo), FORGE_CLI (gh|gt); stdout не трогает.
# Ошибка (nonzero): обнуляет эти переменные, пишет диагностику в stderr
# (без URL и credentials) и НЕ завершает вызывающий shell.
# Читает только `git remote get-url --all origin` и `--push --all origin`:
# эффективные URL, а не raw remote.origin.url, чтобы учитывались insteadOf /
# pushInsteadOf. Никаких сетевых обращений, eval и запуска ssh.

forge_detect() {
  FORGE_PROVIDER=''; FORGE_HOST=''; FORGE_REPO=''; FORGE_CLI=''

  local dir="${1:-.}" fetches pushes all_urls u
  local _FORGE_HOST _FORGE_REPO _provider _cli
  fetches=$(git -C "$dir" remote get-url --all origin 2>/dev/null) || {
    echo "forge_detect: no usable origin remote in: $dir" >&2
    return 1
  }
  pushes=$(git -C "$dir" remote get-url --push --all origin 2>/dev/null) || {
    echo "forge_detect: cannot read push URLs for origin in: $dir" >&2
    return 1
  }
  [ -n "$fetches" ] || { echo "forge_detect: origin has no URLs in: $dir" >&2; return 1; }

  local host='' repo='' provider='' cli=''
  # Построчный обход без word splitting и globbing: не зависит от IFS и
  # опций вызывающего shell (here-string не создаёт subshell).
  all_urls="$fetches"$'\n'"$pushes"
  while IFS= read -r u; do
    [ -n "$u" ] || continue
    _forge_parse_url "$u" || {
      echo "forge_detect: cannot parse origin URL (expected https://host/owner/repo or git@host:owner/repo)" >&2
      return 1
    }
    case "$_FORGE_HOST" in
      github.com)     _provider=github; _cli=gh ;;
      git.flowwow.co) _provider=gitea;  _cli=gt ;;
      *) echo "forge_detect: unsupported forge host: $_FORGE_HOST (expected github.com or git.flowwow.co)" >&2; return 1 ;;
    esac
    if [ -z "$host" ]; then
      host=$_FORGE_HOST repo=$_FORGE_REPO provider=$_provider cli=$_cli
    elif [ "$host" != "$_FORGE_HOST" ] || [ "$repo" != "$_FORGE_REPO" ]; then
      echo "forge_detect: origin fetch/push URLs resolve to different hosts or repositories" >&2
      return 1
    fi
  done <<< "$all_urls"

  FORGE_PROVIDER=$provider FORGE_HOST=$host FORGE_REPO=$repo FORGE_CLI=$cli
  return 0
}

# _forge_parse_url URL — парсит один transport URL в _FORGE_HOST (lowercase,
# без userinfo и порта) и _FORGE_REPO (owner/repo без .git и хвостового /).
# Понимает scheme-формы (https|http|ssh://[user[:pass]@]host[:port]/...)
# и scp-like git@host:owner/repo. Локальный путь или ssh alias (без @) — отказ.
# owner/repo — только [A-Za-z0-9._-], терминальные "." и ".." отвергнуты;
# query/fragment/прочие символы не вычищаются — такой URL малформленный.
_forge_parse_url() {
  local url="$1" authority path owner repo port
  local valid_re='^[A-Za-z0-9._-]+$'
  case "$url" in
    https://*|http://*|ssh://*)
      authority="${url#*://}"; authority="${authority%%/*}"
      path="${url#*://}"; path="${path#*/}"
      [ "$path" != "${url#*://}" ] || return 1  # нет '/' после authority
      authority="${authority##*@}"             # userinfo в результат не идёт
      # Порт обязан быть числом 1..65535. Просто отрезать хвост по ':' нельзя:
      # `https://github.com:bad-port/o/r` тогда считался бы валидным origin.
      case "$authority" in
        *:*)
          port="${authority##*:}"; authority="${authority%:*}"
          case "$port" in ''|*[!0-9]*) return 1 ;; esac
          [ "${#port}" -le 5 ] || return 1
          [ "$((10#$port))" -ge 1 ] && [ "$((10#$port))" -le 65535 ] || return 1
          ;;
      esac
      ;;
    *@*:*)  # scp-like
      authority="${url%%:*}"
      # '/' до ':' — Git считает такой URL локальным путём (scp-интерпретация
      # не применяется); локальный путь не нормализуется в remote-адрес.
      case "$authority" in
        */*) return 1 ;;
      esac
      authority="${authority##*@}"
      [ -n "$authority" ] || return 1  # host после userinfo непустой
      path="${url#*:}"
      ;;
    *) return 1 ;;
  esac
  authority="${authority##*@}"  # userinfo (credentials не попадают в результат)
  path="${path%/}"; path="${path%.git}"
  case "$path" in
    */*) owner="${path%%/*}"; repo="${path#*/}" ;;
    *) return 1 ;;
  esac
  case "$owner" in ''|.|..) return 1 ;; esac
  case "$repo" in ''|.|..) return 1 ;; esac
  [[ "$owner" =~ $valid_re ]] || return 1
  [[ "$repo" =~ $valid_re ]] || return 1
  _FORGE_HOST=$(printf '%s' "$authority" | tr '[:upper:]' '[:lower:]')
  _FORGE_REPO="$owner/$repo"
}
