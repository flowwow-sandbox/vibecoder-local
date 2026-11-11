#!/usr/bin/env bash
# _wt_prune.sh MAIN_WORKTREE — безопасная очистка worktree за `make wt-prune`.
# Удаляет worktree и его локальную ветку ТОЛЬКО при полном доказательстве:
#   • успешный свежий `git fetch --prune` (упавший fetch не подтверждает [gone]);
#   • upstream ветки == [gone], причём tracking ведёт на origin и на одноимённую
#     ветку (у чужого remote/имени [gone] ничего не доказывает);
#   • отсутствие ветки на origin подтверждено read-only `git ls-remote`
#     (exit 2 при пустом выводе): локальный tracking/refspec может быть неполным;
#   • дерево worktree чистое — включая untracked и ignored (.env, app/data):
#     `worktree remove` без --force всё равно удалил бы ignored-файлы;
#   • merged PR в СВОЕЙ forge/repo, где head — эта ветка, а head SHA ровно равен
#     текущему локальному tip (squash ломает ancestry, поэтому SHA, не граф).
# Нет доказательства (closed, чужой fork, другой SHA, ошибка CLI/JSON/страницы,
# ошибка status/ls-remote, нет CLI или jq) → worktree остаётся с предупреждением,
# удаление не делается. CLI выбирается forge_detect по эффективным origin URL;
# чужой CLI не зовётся.

set -u

main="${1:?usage: _wt_prune.sh <main-worktree>}"
. "$(cd "$(dirname "$0")" && pwd)/_forge.sh" || exit 1

if ! forge_detect "$main"; then
  echo "⚠️  wt-prune: не удалось определить основную forge по origin — ничего не удаляю."
  exit 0
fi
if ! command -v "$FORGE_CLI" >/dev/null 2>&1; then
  echo "⚠️  wt-prune: $FORGE_CLI не найден (forge $FORGE_HOST) — merge PR не подтвердить, ничего не удаляю."
  echo "    Установка CLI — make setup."
  exit 0
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "⚠️  wt-prune: jq не найден — ответ CLI не разобрать, ничего не удаляю. Установка — make setup."
  exit 0
fi
if ! git -C "$main" fetch --prune origin; then
  echo "⚠️  wt-prune: git fetch origin упал — [gone] может быть устаревшим, ничего не удаляю."
  exit 0
fi

# _same_repo VALUE — это ровно FORGE_REPO в одной из проверенных форм:
# `owner/repo`, `https://host/owner/repo(.git)` или `git@host:owner/repo(.git)`.
# Прочие формы (в т.ч. `host/owner/repo`) и null — отказ: живой формат head_repo
# не доказан, поэтому fail-closed (ветка не удаляется).
_same_repo() {
  local v="$1"
  [ -n "$v" ] || return 1
  [ "$v" = "$FORGE_REPO" ] && return 0
  _forge_parse_url "$v" 2>/dev/null || return 1
  [ "$_FORGE_HOST/$_FORGE_REPO" = "$FORGE_HOST/$FORGE_REPO" ]
}

# _origin_branch_gone BRANCH — absence proof на origin read-only: только exit 2
# (no matching refs) при пустом stdout. Любой другой код, ошибка или ответ —
# не доказательство (skip), в т.ч. exit 2 с непустым stdout.
_origin_branch_gone() {
  local out
  out=$(git -C "$main" ls-remote --exit-code --heads origin "refs/heads/$1" 2>/dev/null)
  [ "$?" -eq 2 ] || return 1
  [ -z "$out" ]
}

# _clean_worktree PATH — 0 чисто, 1 изменения (tracked/untracked), 2 только
# ignored-записи (.env, app/data требуют ручного разбора), 3 ошибка git status.
# `worktree remove` без --force удаляет ignored-файлы молча, поэтому 2 тоже
# блокирует удаление. Явные флаги: config status.showUntrackedFiles=no не
# должен их скрывать. Ошибка status — отдельный код, не «грязно».
_clean_worktree() {
  local out
  out=$(git -C "$1" status --porcelain --untracked-files=normal --ignored 2>/dev/null) \
    || return 3
  [ -n "$out" ] || return 0
  if printf '%s\n' "$out" | grep -qv '^!! '; then return 1; fi
  return 2
}

# _delete_ref BRANCH TIP — CAS по old-SHA и --no-deref (не разыменовать symref).
# Symref отклоняется вызывающим заранее, до любых side effects.
_delete_ref() {
  git -C "$main" update-ref --no-deref -d "refs/heads/$1" "$2"
}

# _single_array OUT — ровно один JSON-документ, и это массив. `jq -e` на потоке
# смотрит только последний документ, поэтому сначала всё сливается (`-s`).
# Несколько документов/не массив/битый JSON — доказательства нет.
_single_array() {
  printf '%s' "$1" | jq -s -e 'length == 1 and (.[0] | type == "array")' >/dev/null 2>&1
}

# _gh_proof BRANCH TIP — `gh pr list` без --page (локальная help 2.96.0): одна
# выборка с --limit 100, фильтр по head. Не нашли в ней — доказательства нет.
_gh_proof() {
  local out
  out=$(gh pr list -R "github.com/$FORGE_REPO" --head "$1" --state merged --limit 100 \
    --json headRefName,headRefOid,headRepository,headRepositoryOwner) || return 1
  _single_array "$out" || return 1
  # Отсутствующее поле в JSON даёт null → сравнение ложно → skip, а не удаление.
  printf '%s' "$out" | jq -s -e --arg b "$1" --arg s "$2" \
    --arg o "${FORGE_REPO%%/*}" --arg r "${FORGE_REPO#*/}" \
    '[.[0][] | select(.headRefName == $b and .headRefOid == $s
      and .headRepository.name == $r and .headRepositoryOwner.login == $o)] | length > 0' \
    >/dev/null 2>&1
}

# _gt_proof BRANCH TIP — страницы по --limit 100 читаются по порядку; совпадение
# принимается, только если его head_repo — FORGE_REPO. Короткая страница или
# ошибка любой страницы: полного списка нет → доказательства нет.
# Совпадения выбираются jq как строки и проверяются по одной: значение с любым
# control-символом (CR/LF/NUL/tab) отбрасывается до сериализации в строки, иначе
# `head_repo:"a\nteam/demo"` дал бы двух кандидатов и второй мог пройти проверку.
_gt_proof() {
  local page=1 out count candidates repo
  while [ "$page" -le 10 ]; do
    out=$(gt pr list --host "https://$FORGE_HOST" -R "$FORGE_REPO" --head "$1" \
      --state merged --limit 100 --page "$page" \
      --json merged,head,head_repo,head_sha,number) || return 1
    _single_array "$out" || return 1
    count=$(printf '%s' "$out" | jq 'length') || return 1
    # Exit-код jq обязателен: иначе частичный stdout до ошибки (например,
    # [<PR>,5] — печатается head_repo первого элемента, потом падение) прошёл
    # бы как доказательство. Ошибка разбора → safe skip, stderr подавлен.
    candidates=$(printf '%s' "$out" | jq -r --arg b "$1" --arg s "$2" \
      '.[] | select(.merged == true and .head == $b and .head_sha == $s)
         | select((.head_repo | type) == "string")
         | select((.head_repo | test("[[:cntrl:]]")) | not)
         | .head_repo' 2>/dev/null) || return 1
    while IFS= read -r repo; do
      if _same_repo "$repo"; then return 0; fi
    done <<EOF
$candidates
EOF
    [ "$count" -ge 100 ] || return 1
    page=$((page + 1))
  done
  return 1
}

# _merged_proof BRANCH TIP — доказательство merged PR в выбранной CLI/forge.
_merged_proof() {
  [ -n "$2" ] || return 1
  case "$FORGE_PROVIDER" in
  github) _gh_proof "$1" "$2" ;;
  gitea) _gt_proof "$1" "$2" ;;
  *) return 1 ;;
  esac
}

rc=0
tmp=$(mktemp) || exit 1
trap 'rm -f "$tmp"' EXIT
git -C "$main" worktree list --porcelain > "$tmp" || {
  echo "⚠️  wt-prune: git worktree list упал — ничего не удаляю."
  exit 0
}
path=""
while IFS= read -r line; do
  case "$line" in
  "worktree "*) path=${line#worktree } ;;
  "branch refs/heads/"*)
    branch=${line#branch refs/heads/}
    if [ "$path" != "$main" ]; then
      # [gone] — только фильтр кандидатов: tracking обязан быть на origin и на
      # одноимённую ветку (у чужого upstream [gone] ничего не доказывает).
      track=$(git -C "$main" for-each-ref \
        --format='%(upstream:track) %(upstream:remotename) %(upstream:remoteref)' \
        "refs/heads/$branch")
      case "$track" in
      "[gone] origin refs/heads/$branch") ;;
      "[gone]"*)
        echo "⚠️  skip (upstream [gone] относится к другому remote/имени — не доказывает отсутствие origin-ветки): $path  [$branch]"
        path=""
        continue
        ;;
      *)
        # default-arm обязателен: ветка без upstream (как её создаёт `make wt-new`)
        # или с живым tracking не кандидат вовсе.
        echo "⚠️  skip (ветка без [gone]-upstream на origin): $path  [$branch]"
        path=""
        continue
        ;;
      esac
      _clean_worktree "$path"
      case "$?" in
      0) ;;
      1)
        echo "⚠️  skip (uncommitted changes): $path  [$branch]"
        path=""
        continue
        ;;
      2)
        echo "⚠️  skip (в worktree есть ignored-файлы — .env, app/data и подобные требуют ручного разбора): $path  [$branch]"
        path=""
        continue
        ;;
      *)
        echo "⚠️  skip (git status упал, чистота не подтверждена): $path  [$branch]"
        path=""
        continue
        ;;
      esac
      if ! _origin_branch_gone "$branch"; then
        echo "⚠️  skip (origin-ветка не подтверждена отсутствующей): $path  [$branch]"
      else
        tip=$(git -C "$main" rev-parse "refs/heads/$branch" 2>/dev/null)
        if ! _merged_proof "$branch" "$tip"; then
          echo "⚠️  skip (origin-ветка удалена, но merged PR текущего tip не подтверждён — удали вручную, если уверен): $path  [$branch]"
        # Сетевые проверки выше не атомарны с удалением: перечитываем tip,
        # HEAD worktree (именно эта ветка, не только SHA) и чистоту, чтобы не
        # снести коммит, появившийся пока шёл запрос. Остаточная гонка между
        # перечитыванием и update-ref не устраняется — CAS по old-SHA ниже
        # отказывает в удалении, если ref уже ушёл вперёд.
        elif [ "$(git -C "$main" rev-parse "refs/heads/$branch" 2>/dev/null)" != "$tip" ] \
          || [ "$(git -C "$path" symbolic-ref -q HEAD 2>/dev/null)" != "refs/heads/$branch" ]; then
          echo "⚠️  skip (ветка или HEAD worktree изменились во время проверки): $path  [$branch]"
        elif ! _clean_worktree "$path"; then
          echo "⚠️  skip (worktree изменился во время проверки): $path  [$branch]"
        elif [ "$(grep -cxF "branch refs/heads/$branch" "$tmp")" -gt 1 ]; then
          # Ветка вычекнута в двух worktree (возможно только с --force): удаление
          # ref оставило бы второй worktree с висячим HEAD.
          echo "⚠️  skip (ветка занята другим worktree): $path  [$branch]"
        elif git -C "$main" symbolic-ref -q "refs/heads/$branch" >/dev/null 2>&1; then
          # Symref под refs/heads: update-ref удалил бы его target. Отказ до
          # side effects, чтобы не оставить полуудалённое состояние.
          echo "⚠️  skip (символьная ветка, не обычный ref): $path  [$branch]"
        else
          echo "🗑️  removing: $path  [$branch] (PR merged, origin branch gone)"
          if git -C "$main" worktree remove "$path"; then
            # CAS: ref удаляется только если всё ещё равен подтверждённому tip;
            # --no-deref не даёт удалить target символьного ref. Секция branch.*
            # чистится как у `git branch -D`.
            if _delete_ref "$branch" "$tip"; then
              git -C "$main" config --remove-section "branch.$branch" 2>/dev/null || true
            else
              rc=1
            fi
          else
            rc=1
          fi
        fi
      fi
    fi
    path=""
    ;;
  esac
done < "$tmp"
echo "wt-prune: done."
exit "$rc"
