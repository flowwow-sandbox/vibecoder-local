# Forge platform contract

Платформа у проекта одна. Контракт для агента и скриптов: какой forge-CLI
использовать для git-удалённых операций и PR-цикла. Короткие инварианты — в
`AGENTS.md`; платформу выбирает `infra/_forge.sh` (detector), им пользуются
`make setup` и `./infra/start.sh`.

## Как выбирается платформа

- Одна основная forge и repo — по **эффективному** origin (`git remote get-url
  --all origin` и `git remote get-url --push --all origin`): учитываются
  `insteadOf`/`pushInsteadOf`; raw `remote.origin.url` — не источник истины.
- `github.com` → CLI `gh`; `git.flowwow.co` → CLI `gt`. Других хостов нет.
  Fallback, dual-write и override через окружение не предусмотрены.
- Detector выставляет `FORGE_PROVIDER` (github|gitea), `FORGE_HOST`,
  `FORGE_REPO` (owner/repo), `FORGE_CLI` (gh|gt). Неоднозначный или
  непризнанный origin — отказ с диагностикой, а не догадка.
- Root проекта резолвируется по роли скрипта: `./infra/start.sh` — от
  расположения своего скрипта (`infra/`), чтобы запуск из подпапки или чужого
  каталога не определял соседний репозиторий; прочие maintenance-скрипты
  `infra/` — от cwd проекта, где лежит `.env` и идут Git-операции.

## Общий workflow — один, команды — из своей секции

Жизненный цикл изменения (ветка → L1 → review → L2 → PR → squash-merge) описан
в [`dev-workflow.md`](dev-workflow.md) и одинаков для обеих платформ. Команды
PR-цикла берутся из секции своей платформы ниже. Команды одного CLI на другой
forge не переносятся: `gh`-вызов в Gitea-репозитории (и наоборот) — дефект.

Auth (на обеих платформах) доказывает личность и наличие credential, но не
право записи или admin на конкретный репозиторий — доступ проверяется отдельно
и попыткой записи не проверяется.

## GitHub (github.com): gh

- Auth: `gh auth status --active --hostname github.com` (обычный `gh auth
  status` проверяет и посторонние хосты/аккаунты и может отказать из-за них);
  login — руками пилота (`gh auth login --hostname github.com`, device-code
  flow через браузер, агентом не выполняется). Диагностика токена — `gh api
  user --silent --hostname github.com`.
- Явная адресация обязательна: API-вызовы — с `--hostname github.com`;
  `gh repo view` — позиционным `github.com/OWNER/REPO` (у него нет `-R`), а
  `gh pr …` и `gh repo rename` — с `-R github.com/OWNER/REPO`.
  OWNER/REPO — из origin, не из CLI-конфига и не из `GH_HOST`/`GH_REPO`: env
  действуют не всегда, а origin может быть ssh на другого host. Команда без
  `-R` берёт repo из default-конфига или upstream и молча действует на чужом
  проекте.
- Repo: `gh repo view github.com/OWNER/REPO --json name -q .name` — репозиторий передаётся **позиционным аргументом** (`gh repo view` не имеет `-R`/`--repo`; `-R` есть у `gh pr`/`gh repo rename`/`gh run`). Альтернатива для API-полей — `gh api repos/OWNER/REPO --hostname github.com`.
- PR-цикл (номер созданного PR запоминается и используется дальше — `create`
  печатает URL, из него номер и берётся):

  ```bash
  gh pr create --fill -R github.com/OWNER/REPO
  gh pr view N --json state -q .state -R github.com/OWNER/REPO
  gh pr merge N --squash -R github.com/OWNER/REPO
  gh pr list -R github.com/OWNER/REPO
  ```

  Origin-ветка сносится отдельным `git push origin --delete` только после
  подтверждённого `MERGED` у **того же** номера PR (см. dev-workflow §2.7).
- Rename при несовпадении имени репо со slug — подсказка пилоту:
  `gh repo rename -R github.com/OWNER/REPO <slug>` (или Settings веб-интерфейса),
  не автоматическая мутация.

## Gitea (git.flowwow.co): gt

Интерфейс проверен локально по `gt 1.2.0` (справка `gt help`, локальная схема
полей). Живое поведение API `git.flowwow.co` проверено точечно (push-credentials,
merge-flow); прочие флаги и поля ниже ограничены тем, что подтверждено
локальной справкой.

- Установка — только по официальной инструкции
  <https://gitea.com/gitea/cli/releases> (название источника сообщает сам
  `gt --version`). Проверенных brew/apt-пакетов нет — автоматическая установка
  не выполняется, только ручной шаг пилота.
- Auth: `gt auth status --json --verify --host https://git.flowwow.co` —
  выходит 0 при любом исходе, exit 0 недостаточен; принимаются только поля:
  `active=true`, `credential_available=true`, `verified=true`, пустой или
  отсутствующий `error`, и `host` в точности `git.flowwow.co` /
  `https://git.flowwow.co` (допустим terminal slash). Аккаунт чужого инстанса
  или непроверенная credential — отказ. Login —
  руками пилота: `gt auth login --host https://git.flowwow.co`.
- Push/fetch обычным Git по HTTPS-origin: авторизация gt сама по себе
  credentials обычного Git не настраивает. Если `gt repo clone` работает, а
  `git push`/`git fetch` по HTTPS просит Username или падает (`could not
  read Username …` — воспроизведено на клоне без пригодного Git helper;
  уже работающий свой helper заменять не нужно), шаг руками пилота, из
  нужного клона: `gt auth setup-git --local --host https://git.flowwow.co` —
  прописывает repo-local http helper в конфиг этого клона. Без `--local`
  helper уйдёт в global-конфиг и может заместить прежние helpers этого host.
  `gt auth status` даже с `verified` не доказывает push. SSH-origin
  использует свой SSH key — helper не нужен.
- Явная адресация обязательна на каждом вызове: `--host https://git.flowwow.co`
  (перекрывает `default_host` из конфига gt) и `-R OWNER/REPO` (перекрывает
  git remote и `gt.repository` из конфига; OWNER/REPO — из origin).
- Repo: `gt repo view --json name -R OWNER/REPO --host https://git.flowwow.co`.
  Уровень доступа к репозиторию CLI не отдаёт — «могу ли я пушить» пробами
  не проверяется.
- PR-цикл (номер созданного PR используется при merge и подтверждении):

  ```bash
  gt pr create --fill --yes -R OWNER/REPO --host https://git.flowwow.co
  gt pr view N --json merged,head_sha -R OWNER/REPO --host https://git.flowwow.co
  gt pr merge N --squash --yes --delete-branch=false -R OWNER/REPO --host https://git.flowwow.co
  gt pr list -s open -R OWNER/REPO --host https://git.flowwow.co
  ```

  (`--yes` обязателен в скриптах: без него create/merge запрашивают
  подтверждение. `--delete-branch=false` обязателен тоже: с ним head-ветка
  остаётся для отдельного удаления, а без явного `false` поведение наследует
  настройку репозитория — merge может снести ветку сам.)
  Merge подтверждается полем `merged == true`, а не интерпретацией
  `state == closed`: закрыть PR можно и без слияния. Origin-ветка удаляется
  только после этого подтверждения.
- Rename при несовпадении имени репо со slug — подсказка пилоту:
  `gt repo rename <slug> -R OWNER/REPO --host https://git.flowwow.co` (есть
  `--dry-run`) или Settings репозитория на git.flowwow.co; не автоматическая
  мутация и не `gh repo rename`.

## Чего делать нельзя

- Запускать `gt auth token` и выводить credentials в логи: команда печатает
  сам токен.
- Смешивать CLI и платформы: флаги одного CLI не переносятся на другой
  (`--hostname` есть только у gh, `--host` — только у gt; `-R` у обоих, но
  принимает разные формы).
- Выдавать permissions/available за репозиторий на Gitea: CLI этого поля не
  отдаёт — не выдумывать его и не проверять доступ попыткой записи.
- Ставить gt из неподтверждённых пакетов: только официальная инструкция выше.
