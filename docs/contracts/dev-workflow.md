# Development workflow

Жизненный цикл одного изменения от запроса оунера до зелёного локального запуска. SSOT — этот файл; короткие инварианты — в `AGENTS.md`.

## 1. Verification layers (trust model)

| Layer | Что | Где |
|---|---|---|
| **L1** | self-check: lint + tests (если есть в стеке) + type check | локально перед preview |
| **L2** | local preview: оунер открывает `http://localhost:<port>` и говорит «ок» | локально |

L2 не автоматизируется. Без явного «ок» от оунера — не открываем PR.

## 2. Lifecycle одного изменения

### 2.1 Pre-work
Понять задачу от оунера. Если непонятно — переспросить (см. AGENTS.md принцип №1). Важно: НЕ начинать кодить пока не ясен критерий приёмки.

Если задача — нетривиальная фича (несколько файлов, новые абстракции, несколько шагов) — вызови `superpowers:brainstorming` ДО кода. Если bug — вызови `superpowers:systematic-debugging`.

**Если фича создаёт новую call surface наружу** (HTTP-endpoint кроме `/healthz`, MCP tool, webhook receiver, публичная форма, file upload) — пройди pre-flight чек-лист из `./audience-and-exposure.md` §4 с оунером **до начала кода**. Чек-лист определяет тир (T1 / T2 / T3) и какие защиты (rate-limit, кэш, hard pagination limits) обязательны для тира.

### 2.2 Реализация в feature-ветке (worktree)

Каждая фича разрабатывается в отдельной ветке `feature/<slug>` (не в `main`). Рекомендуемый способ — через worktree: `make wt-new SLUG=<slug>` (из основной папки репо) создаёт worktree в `.worktrees/<slug>/` (внутри репо, в `.gitignore`) с уже переключённой веткой; работать продолжаешь там. Worktree даёт физическую изоляцию: можно держать локальный сервер фичи A запущенным в одной папке и параллельно начать фичу B в другой, без `git stash` / переключения веток / потери running state.

**Создавай worktree только через `make wt-new`** — не через native «create worktree» агент-харнесса или IDE. После merge'а отработавшие worktree снимай командой `make wt-prune`.

**Синхронизацию с origin `wt-new` делает сам:** `git fetch origin main`, fast-forward локального `main` и ветвление `feature/<slug>` именно от `main`. Иначе фича стартовала бы со старой базы (влит чужой PR, поработали с другого ноутбука) — в diff'е PR всплывают чужие изменения, а merge ловит конфликты. Два случая, когда таргет останавливается:

- **Нет сети / origin недоступен** — офлайн-обход `make wt-new SLUG=<slug> NO_FETCH=1`: синхронизация пропускается, ветка идёт от локального `main`. Обычная работа — без этого флага.
- **Fast-forward невозможен** — значит в локальном `main` есть коммиты, которых нет в origin, а прямой push в `main` запрещён (см. `./safety-rules.md` §3). Посмотри их (`git log origin/main..main`), перенеси в feature-ветку и повтори.

Если worktree-инструментария ещё нет в проекте — fallback в текущей рабочей папке: `git switch main` → `git pull --ff-only origin main` → `git checkout -b feature/<slug>`. Синхронизацию тогда делаешь руками, и `git switch main` в ней обязателен: `git pull --ff-only origin main`, запущенный на feature-ветке прошлой задачи, вольёт origin/main **в неё**, локальный `main` останется старым, а новая ветка уедет от чужой фичи — её коммиты всплывут в следующем PR.

Кодируй атомарно: одно логическое изменение = один потенциальный коммит. Соблюдай AGENTS.md принципы (особенно №2 «Простота» и №3 «Хирургические изменения»).

### 2.3 Self-check (L1)
Запусти всё, что доступно в твоём стеке:
- Линтер: `eslint`, `ruff`, `bun lint` — что подходит.
- Тесты: `vitest`, `pytest`, `bun test`, `node --test` — что подходит.
- Тайпы: `tsc --noEmit`, `mypy` — если используется типизация.

Если что-то падает — исправляй перед preview, не неси оунеру битое.

### 2.4 Commit (в feature-ветке)

Атомарные коммиты в imperative mood («add slug validation», не «added»). Первая строка ≤ 72 символа. Conventional commits (`feat:`/`fix:`/`docs:`) НЕ требуются — свободный текст.

**Auto-commit policy:** после завершения атомарной задачи и зелёного L1 (lint + tests + typecheck в стеке) — `git commit` в feature-ветке. Если L1 красный — НЕ коммитить, фиксить.

Коммит идёт **до** cross-review и L2 не случайно: субагент на §2.5 читает `git diff main...feature/<slug>`, и committed состояние даёт чистый diff (без шума из working tree типа неудалённых `console.log` / debug-следов / случайных правок в соседних файлах). Коммиты живут только в feature-ветке — в main попадут только после merge PR (§2.7), переделывать локально безопасно.

### 2.5 Cross-review через субагент (обязательно)

Перед показом оунеру на L2 — вызови `superpowers:requesting-code-review`. Это запускает субагента в той же сессии, который читает diff feature-ветки (`git diff main...feature/<slug>`) и возвращает замечания. Это **обязательный** шаг, а не опциональный: cross-review субагентом ловит ошибки, которые автор-агент пропускает (в Codex, где skill'ов и субагентов нет — отдельный review-проход по diff'у в новом контексте).

Фиксы по замечаниям — атомарными коммитами в той же feature-ветке. Когда review зелёный — переходи к §2.6.

### 2.6 Local preview (L2, обязательно)

Это последний gate перед PR — с участием оунера. К этому моменту код уже прошёл L1 (§2.3), закоммичен (§2.4) и проревьюен субагентом (§2.5), оунеру приносим уже отполированную версию.

1. Подними локальный preview:
   - Если ты ещё на стартовой заглушке (static HTML без стека) — `make preview` из корня репо: он сам читает `app/index.html.tpl` и открывает файл в браузере.
   - Когда добавлен стек — поднимай локальный сервер из `app/`: `cd app && node server.js` / `cd app && bun dev` / `cd app && python app.py` / эквивалент. После миграции на стек `make preview` неактуален (он рендерит только заглушку `app/index.html.tpl`) — preview = запуск реального приложения.
2. Дай оунеру URL: `http://localhost:<port>/<path-к-изменению>`.
3. Кратко (1-2 предложения) опиши что изменилось и где конкретно смотреть.
4. Дождись «ок» (или двигайся по фидбэку).

**Это не «pre-flight check на дёрнутость» — это полная визуальная приёмка.** Без неё PR не открываем (AGENTS.md инвариант #1).

**Если оунер сказал «не ок»:**
- Правки по фидбэку → новый коммит в той же feature-ветке, **не `--amend` и не `--force`**. Разница в природе запрета: `--force` / `--force-with-lease` блокирует хук, а `--amend` хук пропускает — его запрещает правило, потому что коммит уже видел ревьюер (§2.5), а после push переписывание истории равносильно force-push (`./safety-rules.md` §3.2). Squash-merge в §2.7 всё равно сольёт всю историю ветки в один коммит main, так что fixup-коммиты — нормально.
- Если правки нетривиальные (меняют структуру, не только текст/цвета) → краткий повторный cross-review (§2.5) только на дельту.
- Повторный L2 → оунеру.
- Когда оунер сказал «ок» — переходи к §2.7.

### 2.7 PR + merge

Push feature-ветки и открой PR:

```bash
git push -u origin feature/<slug>
gh pr create --fill                        # или с явным title/body
gh pr merge --squash                       # squash-merge на GitHub (без локальной чистки)
# origin-ветку удаляй ТОЛЬКО когда PR реально MERGED: при branch-protection/merge-queue
# merge откладывается, и преждевременное удаление снесёт ветку, которая ещё нужна GitHub'у.
[ "$(gh pr view --json state -q .state)" = "MERGED" ] && git push origin --delete feature/<slug>
```

`--squash` сворачивает все коммиты feature-ветки в один коммит main (чистая история).

> **Почему НЕ `gh pr merge --delete-branch` из worktree:** чтобы удалить локальную `feature/<slug>`, gh сначала переключается на `main` (`git checkout main`), а `main` закреплён за основным worktree → `fatal: 'main' is already used by worktree`. Merge на GitHub к этому моменту уже прошёл бы, но команда падает (и провоцирует повторный merge). Поэтому: merge без `--delete-branch`, а origin-ветку сноси отдельным `git push origin --delete` — он remote-only, из worktree отрабатывает без ошибок.

Локальную чистку делает `make wt-prune` из основного worktree: вернись в корень репо (`cd`), синхронизируй main (`git pull --ff-only`) и запусти `make wt-prune` — она снимает worktree, чьи origin-ветки уже удалены (PR влит), и удаляет их локальные ветки; worktree с незакоммиченными изменениями пропускает с предупреждением. Точечно — `git worktree remove .worktrees/<slug>`.

**Branch model:** разработка в feature-ветке `feature/<slug>` → commit (§2.4) → cross-review субагентом (§2.5) → local preview (§2.6) → PR → squash-merge в main. Прямой `git push origin main` запрещён политикой (см. `./safety-rules.md` §3).

## 3. Rollback

- **Код проблемный (default):** revert обычным worktree+PR-flow (§2.2/§2.7): `make wt-new SLUG=revert-<slug>`, в нём `git revert <hash>` → `git push -u origin feature/revert-<slug>` → `gh pr create --fill` → merge как в §2.7 (`gh pr merge --squash` + `git push origin --delete feature/revert-<slug>`) → из основного worktree `git pull --ff-only` + `make wt-prune`. Cross-review для revert'а опционален — diff тривиальный.
- **Emergency-revert (нужно немедленно):** допускается прямой `git revert <hash> && git push origin main` **только** с явного «ок» оунера в моменте. Зафиксируй в чате с оунером, что это override default'а.

## 4. Когда вызывать субагентов (через obra/superpowers)

| Ситуация | Skill |
|---|---|
| Нетривиальный bug (3+ места, неясная причина) | `superpowers:systematic-debugging` |
| Большая фича / архитектурное решение | `superpowers:brainstorming` → `writing-plans` |
| Перед L2 — cross-review субагентом (**mandatory**, см. §2.5) | `superpowers:requesting-code-review` (в Codex, где skill'ов и субагентов нет — отдельный review-проход по diff'у в новом контексте) |
| Реализация по готовому плану | `superpowers:executing-plans` или `subagent-driven-development` |

## 5. Conventions

### 5.1 Branches & commits

- **Branch model:** `main` всегда зелёный. Разработка в feature-ветке `feature/<slug>` (рекомендуется через worktree, `make wt-new SLUG=<slug>`) → commit (§2.4) → cross-review субагентом (§2.5) → L2 (§2.6) → PR → squash-merge в main. Прямой `git push origin main` запрещён политикой (см. `./safety-rules.md` §3). Исключение — emergency-revert (см. §3).
- **Commit-сообщения:** imperative mood (`add slug validation`, не `added`), ≤ 72 символа в первой строке. Свободный текст; conventional commits (`feat:`/`fix:`) НЕ требуются.
- **Атомарность:** один логический change = один коммит в feature-ветке. Если коммит > 300 строк изменений — скорее всего его надо разделить. При squash-merge все коммиты feature-ветки сворачиваются в один на main — заголовок PR станет заголовком squash-коммита, поэтому формулируй его осмысленно.
- **PR-merge (из worktree):** `gh pr merge --squash` + `git push origin --delete feature/<slug>` — НЕ `--delete-branch` (из worktree его локальная чистка упрётся в `main`, занятый основным worktree; см. §2.7). Затем из основного worktree: `git pull --ff-only` + `make wt-prune`.
- **После merge:** из основного worktree `git pull --ff-only` синхронизирует локальный main (из feature-worktree `git checkout main` упрётся в занятую ветку — см. §2.7).

### 5.2 Security

Никогда:
- `git commit --no-verify` (наш custom git-no-verify-guard в `.claude/hooks/` заблокирует — wiring в `.claude/settings.json` для Claude Code и в `.codex/hooks.json` для Codex).
- `git push --force` / `git push --force-with-lease` (потеря истории; на main вообще запрещено).
- `npm install --ignore-scripts=false` (выключает supply chain protection из `.npmrc`).
- `npm publish` (этот репо не публикуется в npm).
- `gh auth logout` (без явного запроса оунера).
- Чтение `.env` в код приложения — секреты идут через `process.env` / `os.environ`, не через `fs.readFileSync('.env')`.

Всегда:
- `.env` в `.gitignore`.
- Секреты — только через `.env` (не в коде, не в коммитах).

См. полный список — `./safety-rules.md`.
