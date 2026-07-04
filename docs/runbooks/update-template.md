# Runbook: update-template

**Триггер от оунера** (фраза, активирующая этот runbook): «обнови шаблон проекта»

**Предусловие:** онбординг пройден (`gh auth status` зелёный), working tree чистый — незакоммиченные правки сначала закоммить в их feature-ветку (или явно отложить с оунером).

**Постусловие:** изменения template'а с момента последней синхронизации перенесены в проект через PR по стандартному dev-workflow; в корне лежит обновлённый `.template-version`; приложение локально поднимается.

**Зачем это.** Твой репозиторий создан из template'а `flowwow-sandbox/vibecoder-local` через «Use this template» — общей git-истории с ним нет, и забрать изменения template'а обычным `git pull` невозможно. Template при этом развивается: правки хуков безопасности, контрактов, infra-скриптов. Этот runbook переносит его изменения пофайлово, не затирая правки твоего проекта.

## Шаги

1. **Проверь working tree.** `git status` — если есть незакоммиченные изменения, сначала разберись с ними (закоммить в текущую feature-ветку). Обновление шаблона стартует от чистого `main`.

2. **Подключи upstream и забери его историю.**

   ```bash
   git remote add template https://github.com/flowwow-sandbox/vibecoder-local.git 2>/dev/null \
     || git remote set-url template https://github.com/flowwow-sandbox/vibecoder-local.git
   git fetch template
   ```

   Sanity-check происхождения (не обязателен, но дёшев): `tpl=$(gh api "repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)" --jq '.template_repository.full_name') || tpl=""` — если `tpl` непуст и НЕ равен `flowwow-sandbox/vibecoder-local`, остановись и спроси оунера: репо создан из другого шаблона, этот runbook к нему не применим.

3. **Определи базу сравнения** — коммит template'а, соответствующий текущей копии проекта:

   ```bash
   if [ -f .template-version ]; then
     BASE=$(awk '{print $2}' .template-version)
   else
     ROOT_DATE=$(git log --max-parents=0 --format=%aI HEAD | tail -1)
     BASE=$(git rev-list -1 --before="$ROOT_DATE" template/main)
   fi
   ```

   Логика: root-коммит репо, созданного из template'а, датирован моментом создания — состояние template'а на эту дату и есть то, что лежит в копии. После первого прогона база хранится в `.template-version` (см. шаг 7) и прогоны инкрементальны.

   Если `BASE` пуст (история template'а пересоздавалась — аномалия): возьми `BASE=$(git rev-list --max-parents=0 template/main)`, предупреди оунера, что diff будет аномально большим, и действуй максимально консервативно (больше показывай, меньше применяй молча).

4. **Прочитай, что изменилось.** `git log --stat "$BASE"..template/main` — сообщения sync-коммитов человекочитаемы (`sync from sandbox-meta@<sha>: <что изменилось>`). Если список пуст — скажи оунеру «шаблон не менялся с последней синхронизации» и заверши (ничего коммитить не нужно). Иначе изучи пофайловый diff: `git diff "$BASE"..template/main`.

5. **Заведи ветку.** Стандартно: `make wt-new SLUG=template-update-<YYYY-MM-DD>` и работай в worktree этой ветки.

6. **Перенеси изменения пофайлово.** Для каждого файла из diff'а шага 4 определи, менялся ли он в проекте относительно базы:

   ```bash
   git diff "$BASE":<path> HEAD:<path>
   ```

   (diff двух блобов работает несмотря на unrelated histories. Для файлов, помеченных в diff'е шага 4 как `new file`: если такого пути в проекте нет — сразу бери версию template'а; если файл с таким путём в проекте уже есть (создан независимо) — это ветка «меняли оба», мерджи вручную. На файле, отсутствующем с одной из сторон, команда вернёт `fatal: … does not exist` с ненулевым кодом — это не сбой процедуры, а сигнал «новый либо удалённый файл».)

   - **В проекте не менялся** → возьми версию template'а: `git checkout template/main -- <path>`. Файл, удалённый в template'е и не тронутый в проекте, — удали (`git rm <path>`).
   - **Менялся и в проекте, и в template'е** (типовой случай — `infra/Dockerfile` после смены стека) → НЕ перезаписывай: вплети изменения template'а в версию проекта вручную, сохранив правки проекта, и покажи оунеру, что и почему изменилось.
   - **Не переноси никогда:** `app/**` (там живёт приложение проекта — изменения дефолтного стаба template'а только упомяни в резюме), `.env`, `.env.example` (удалён при онбординге — правки в нём неактуальны), `.template-version` (обновишь сам на шаге 7).

7. **Обнови маркер.** В той же ветке:

   ```bash
   echo "flowwow-sandbox/vibecoder-local $(git rev-parse template/main) $(date -u +%Y-%m-%dT%H:%M:%SZ)" > .template-version
   git add .template-version
   ```

8. **Проведи через стандартный flow.** Как обычную фичу (см. `docs/contracts/dev-workflow.md` §2): commit → L1 (lint + tests + typecheck проекта) → cross-review → L2 (local preview, «ок» оунера) → push → PR → squash-merge.

9. **После merge — проверь локальный запуск.** Подними приложение командой его стека (`bun dev`, `npm run dev`, `uvicorn` и т.п.) — оунер видит его локально. `infra/start.sh` приложение не запускает (он только готовит окружение). Если не поднимается — runbook `troubleshooting.md`.

10. **Резюме оунеру.** Перечисли: какие изменения затянуты (по сообщениям коммитов template'а), что пропущено (`app/**`, `.env*`) и почему, какие файлы мерджились вручную и как решены конфликты. Отдельно предупреди: если обновились `.claude/hooks/**`, `.claude/settings.json` или `.codex/**` — изменения вступят в силу после перезапуска агент-сессии.
