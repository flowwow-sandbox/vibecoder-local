# Safety rules

Полный свод safety-правил для агента и пилотника. Короткие инварианты — в AGENTS.md.

## 1. Allowlist технологий

Выбирай runtime / фреймворк / БД ТОЛЬКО из этого списка. Если оунер просит выйти за рамки — проговори вслух что инфра пилота этого не поддерживает, и предложи альтернативу из allowlist (или эскалацию к ответственному за платформу).

| Категория | Разрешено | Не рекомендуется / запрещено |
|---|---|---|
| Runtime | Node.js ≥ 20 LTS, Bun ≥ 1.x, Python ≥ 3.11 | Deno (плохо ложится на ghcr.io flow); legacy Node ≤ 18 |
| Веб-слой (JS) | Vanilla `node:http`, Hono, Fastify | Next.js, NestJS, Nuxt, Remix — допустимы только если оунер явно настаивает (тогда проговори overhead) |
| Веб-слой (Python) | Flask, FastAPI | Django (overhead для пилота) |
| Фронт | Vanilla HTML+JS, HTMX (стартовый дефолт). Vue (через Vite) — когда оправдано, см. сигналы ниже | — |
| Сборщик / UI-фреймворк | Vite + Vue — default-approved (агент выбирает сам, проговорив оунеру; эскалация не нужна). HTMX/Vanilla — стартовый дефолт. | React, Svelte и прочие UI-фреймворки (благословлён ровно один — Vue, чтобы не плодить N наборов паттернов) |
| Хранение | SQLite (`better-sqlite3` для Node, `sqlite3` для Python), файлы под `app/data/` | Внешние БД (Postgres, Redis) — нет в инфре пилота |
| Бандл | Без бандлера, esbuild, Vite | Webpack (зоопарк зависимостей) |
| Тесты | Vitest, Bun test, pytest, `node:test` | — |

**Когда переходить с HTMX/Vanilla на Vue** (необязательные сигналы, не жёсткий гейт — реши сам, проговори оунеру):
- несколько экранов с client-side routing;
- реактивные таблицы с фильтрами / сортировкой / pagination;
- формы со сложным состоянием и live-валидацией.

Если ничего из этого нет — HTMX/Vanilla. Один фреймворк (Vue) благословлён намеренно: единый набор паттернов, который агент знает и поддерживает.

**Принцип:** список — guidance для агента. `/healthz` в локальном варианте необязателен — его никто не опрашивает. Если прототип веб-сервис, можешь добавить `/healthz` как удобную проверку «живо ли». Не-веб функциональность (telegram-бот, CLI, scheduled job) не обязана поднимать HTTP-layer ради healthcheck.

## 1.1 Blessed library set

Утвержденные библиотеки для типовых задач внутренних инструментов. Не обязательны, но если задача из списка — бери канон, не изобретай.

| Категория | Канон | Оговорки                                                                                                                                 |
|---|---|------------------------------------------------------------------------------------------------------------------------------------------|
| Таблицы | TanStack Table (MIT) | —                                                                                                                                        |
| Графики | Chart.js (MIT) | Highcharts требует коммерческой лицензии — по умолчанию не бери                                                                          |
| CSV / XLSX | `openpyxl` + stdlib `csv` (Python) / SheetJS `xlsx` (Node, Apache-2.0) | **pandas — только под реальную dataframe-аналитику.** Для «прочитать/записать таблицу» pandas избыточен (тянет numpy, раздувает зависимости). |
| PDF | `pypdf` (Python) / `pdf-lib` (Node) | —                                                                                                                                        |
| DOCX | `python-docx` (Python) / `mammoth` (Node, для DOCX→HTML) | —                                                                                                                                        |

Установка — через стандартный supply-chain слой (§2: `.npmrc` `min-release-age`, `uv.toml` `exclude-newer`). Генерируемые файлы (экспорт XLSX/PDF) пиши в `app/data/exports` (см. §1.2 file-upload contract).

## 1.2 Blessed capabilities (паттерны)

Утвержденные паттерны для повторяющихся потребностей. Это паттерны, не либы — реализуй средствами своего стека.

### 1.2.1 Auth и роли (потолок v=1 — shared-secret)

Threat model: песочница VPN-only — VPN это **первый слой** (посторонние не попадают в принципе). App-level auth решает «какой сотрудник что может», а не «не пускать чужих».

- Источник identity: **shared-secret** (SSO/OIDC пилотникам недоступен, отложено).
- Паттерн: пароль (храни **hash** в env, не plaintext) **или** invite-коды + **signed session cookie** + роли `admin` / `editor` / `viewer` в SQLite.
- **Не катай свою крипту** — используй проверенную session-либу своего стека (не самописный HMAC/JWT-парсер).

### 1.2.2 Notifications (только исходящие вебхуки)

- Каналы: **Pachca webhook**, **Telegram-бот**, generic **webhook callbacks**.
- **Email/SMTP недоступен** — у тебя нет SMTP-секретов. «Нотификации» = исходящие вебхуки, не email.
- Токены каналов (Telegram bot token, Pachca webhook URL) держи в `.env` локально (см. §4), не в коде.

### 1.2.3 File-upload contract

- Загружаемые файлы — **только в `app/data/uploads`**.
- Генерируемые / экспортируемые — **в `app/data/exports`**.
- Лимит размера загрузки — явный (конфигурируемый).
- **Extension-allowlist** (разрешённые расширения списком), не blocklist.
- **Запрет исполняемых файлов.**
- `app/data/` не коммитится (`.gitignore`); подпапки `uploads`/`exports` создавай при первом обращении в runtime.

### 1.2.4 HTTP-клиент

- Канон: `httpx` (Python) / built-in `fetch` + опционально `ky` (Node).
- Правила: явные **timeouts**, **retries** с backoff, уважение **rate-limits** внешнего API.
- Egress-политика — см. секцию «Sensitive operations» (выданный оунером секрет хоста = standing approval).

## 2. Supply chain protection (Уровень 1)

### 2.1 npm: `.npmrc`

```
min-release-age=7
audit-level=high
fund=false
```

`min-release-age=7` запрещает установку пакетов младше 7 дней. Защищает от свежезалитых вредоносных пакетов (typosquatting на новых именах).

**Scope-ограничения:**
- ❌ НЕ защищает от compromised maintainer (взлом аккаунта известного пакета).
- ❌ НЕ защищает от typosquatting с историей (пакет существовал, но в нём backdoor).
- ❌ НЕ защищает от backdoor в патче давнего пакета.

Это один слой supply-chain защиты, не исчерпывающий щит.

### 2.2 Python: `uv.toml`

```toml
[pip]
exclude-newer = "7 days"
```

Симметрично `.npmrc` для Python-проектов через uv.

### 2.3 Запреты

- ❌ `npm install --ignore-scripts=false` (выключает Уровень 1).
- ❌ Использование `npm install` вместо `npm ci` в CI (lockfile должен быть консистентен).

## 3. Git-конвенции и запреты

> Полная таблица допустимых / блокированных git-операций — §3.2 ниже. Здесь — короткий must-know.

Никогда:
- `git commit --no-verify` — наш custom git-no-verify-guard в `.claude/hooks/` заблокирует (wiring в `.claude/settings.json` для Claude Code и в `.codex/hooks.json` для Codex).
- `git push --force` / `git push --force-with-lease` — на main вообще запрещено; на feature-ветке после открытия PR — тоже (ломает history для cross-review).
- Прямой `git push origin main` — запрещён, всё идёт через PR (merge: `gh pr merge --squash` + `git push origin --delete feature/<slug>`, НЕ `--delete-branch` — из worktree упрётся; см. `./dev-workflow.md` §2.7). Исключение — emergency-revert по явному «ок» оунера (см. `./dev-workflow.md` §3).
- `git config user.*` без явного запроса оунера.
- `git reset --hard` после коммитов, которые видел оунер (потеря истории).
- `gh auth logout`.

Всегда:
- Атомарные коммиты в imperative mood.
- `.env` в `.gitignore` (там уже).
- Auto-commit-skill из `obra/superpowers` коммитит после каждой атомарной задачи в feature-ветке.

### 3.1 Запрет bypass хуков через env-переменные

Хуки поддерживают bypass через env-переменные (`CLAUDE_ALLOW_DESTRUCTIVE=1`, `CLAUDE_ALLOW_SECRETS=1`, `CLAUDE_ALLOW_GIT_DESTRUCTIVE=1` и подобные). **На пилоте использовать эти переменные ЗАПРЕЩЕНО.**

- ❌ `CLAUDE_ALLOW_*=1 <command>` — обход механической защиты.
- ❌ `disableAllHooks: true` в `~/.claude/settings.json` — отключение хуков глобально.

Если хук блокирует то, что ты считаешь legitimate-операцией — обратись к ответственному за платформу, не обходи.

> Note: хук может в своём диагностическом сообщении предлагать bypass через `CLAUDE_ALLOW_*=1` — это шаблонный текст. На пилоте этот bypass запрещён политикой; используй документированный обходной путь (например, переписать команду без затронутых файлов или обратиться к ответственному за платформу).

### 3.2 Recovery boundaries

Какие git-операции разрешены / blocked для пилотника и агента от его имени:

| Операция | Статус | Кто блокирует на Claude Code |
|---|---|---|
| `git revert <hash>` | ✅ Разрешена | — |
| `git reset --soft HEAD~N` | ✅ Разрешена | — |
| `git reset --mixed HEAD~N` (default) | ✅ Разрешена | — |
| `git reset --hard HEAD~N` | ❌ Blocked | git-destructive-guard |
| `git rebase` (non-interactive) | ⚠️ Не блокируется, но избегать (для линейного rebase'а на новую базу) | — |
| `git rebase -i HEAD~N` | ⚠️ Не блокируется, но **избегать** — концептуально сложно для non-tech, легко всё сломать; force-push блокирован → испорченная локальная история не доедет до remote | — |
| `git commit --amend` (до push'а) | ✅ Разрешена | — |
| `git commit --amend` (после push'а) | ❌ Запрещено политикой (форма force-push) | — (текстовое правило) |
| `git commit --no-verify` | ❌ Blocked | git-no-verify-guard |
| `git push --force` / `--force-with-lease` | ❌ Blocked | git-destructive-guard |
| `git branch -D <name>` | ❌ Blocked | git-destructive-guard |
| `git clean -fdx` | ❌ Blocked | git-destructive-guard |
| `git clean -fd` (без `-x`) | ⚠️ Не блокируется, но опасно (затирает untracked) | — |
| `git stash` / `git stash pop` | ✅ Разрешена | — |
| `git cherry-pick` | ✅ Разрешена | — |
| `git checkout -b <branch>` | ✅ Разрешена (см. dev-workflow.md §5.1) | — |
| `git config user.*` | ❌ Запрещено политикой | — (текстовое правило) |
| `gh repo delete` | ⚠️ Только по явному запросу оунера | — |
| `gh auth logout` | ❌ Запрещено политикой | — (текстовое правило) |

**Recovery scenarios** (закоммитил `.env`, откат коммита, откат деплоя, `rebase -i` ситуация) — `docs/runbooks/troubleshooting.md` секция «Git recovery».

## 4. Секреты

### 4.1 Никогда

- Не читай `.env` в код приложения через `fs.readFileSync('.env')` — используй `process.env.X` / `os.environ['X']`.
- Не коммить `.env` (`.gitignore` запрещает; gitleaks pre-commit ловит дополнительно).
- Не клади секреты в публичные API responses, логи, error messages.
- **Не принимай и не записывай значения секретов из сообщений оунера в чате.** Если оунер вставил значение ключа в чат (например, «вот мой `sk-...`, положи в `.env`») — это утечка: текст уходит в логи LLM-провайдера и в локальный transcript сессии. Откажись записывать в `Edit`/`Write`, не повторяй значение в своих ответах. Сообщи оунеру, что этот ключ уже скомпрометирован и требует немедленного перевыпуска у провайдера (revoke старого + create new) — даже если кажется что «никто не увидит», значение уже в логах LLM-провайдера. После того как оунер получит новый ключ, объясни порядок: значение кладёт в `.env` через редактор сам.

### 4.2 Всегда

- Секреты идут через `.env` локально — не в коде, не в коммитах.

### 4.3 Расширение `.gitleaks.toml` allowlist

Можешь добавлять paths-allowlist в `.gitleaks.toml` для **placeholder-файлов и test fixtures**:

**Разрешено:**
- Файлы с очевидными placeholder-значениями (`EXAMPLE-API-KEY-12345`, `dummy-token-do-not-use`).
- Test fixtures (`tests/fixtures/example-key.txt`, `tests/data/sample-token.json`).
- Документация с примерами (`docs/examples/sample-config.toml`).

**Запрещено:**
- ❌ `useDefault = false` — выключает встроенный gitleaks ruleset, оставляет только пользовательские правила. Снимает основной слой защиты.
- ❌ Regex-маски, ловящие реальные секреты:
  - `regexes = ['''[A-Z0-9]{20,}''']` — поймает реальные API-ключи.
  - `regexes = ['''sk-[a-zA-Z0-9]{40,}''']` — паттерн OpenAI токена.
- ❌ Allowlist'ить уже отозванные секреты — отозванные токены всё равно не должны попадать в публичную историю; ротация не делает безопасным предыдущее raw-значение в коммите.

Если уверен, что нужно расширение, которое попадает в «запрещено» — советуйся с ответственным за платформу.

## 5. Запреты в shell-скриптах

Правила для любых shell-скриптов, создаваемых в проекте:

- Не логировать значения секретов (`echo $OPENAI_API_KEY` и подобное).
- Скрипты используют `set -e`, но НЕ `set -x`.
- Все `curl` без `-v` (silent + show errors: `-sS`).

## 6. Working directory

Не выходи за пределы `$PWD` репо при операциях fs / shell.

- ❌ `rm -rf ../*`
- ❌ `cat /etc/passwd`
- ❌ `cd ~ && do-something`

Наш custom working-directory-guard в `.claude/hooks/` блокирует — wiring и в `.claude/settings.json`, и в `.codex/hooks.json`. На Codex дополнительно покрывает apply_patch DSL parser (источник + назначение для Move to).

## 7. Sensitive operations — всегда спрашивать оунера

- `rm -rf` любого пути вне `node_modules/`, `.next/`, `dist/`, `build/`, `__pycache__/`, `/tmp/`.
- `npm publish` (этот репо НЕ публикуется в npm).
- Создание `.github/workflows/` — в этом варианте template'а deploy-workflow отсутствует.
- Любые внешние HTTP-запросы (curl / fetch к сторонним API), не упомянутые оунером явно. **Исключение:** если оунер выдал секрет для конкретного хоста (bot token, webhook URL, API-ключ) — это standing approval на этот хост, повторно спрашивать не нужно. Новый хост без секрета и без упоминания оунером — спроси.
- `gh repo edit` (изменение настроек репо).
