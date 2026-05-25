# Sources

## AnastasiyaW hooks
- Repository: https://github.com/AnastasiyaW/claude-code-config
- License: MIT (see LICENSE-anastasiyaw)
- Imported commit: 866045610b5d0079136bf46771c48d8d7e7ce19e
- Imported date: 2026-05-08
- Files imported: secret-leak-guard.py, api-key-leak-detector.py, destructive-command-guard.py, git-destructive-guard.py, command-injection-guard.py, safety_common.py

## Custom hooks (написаны нами в стиле AnastasiyaW)
- git-no-verify-guard.py — блокирует `git commit --no-verify`
- working-directory-guard.py — блокирует выход за пределы корня репо

## Local modifications (deviations from upstream AnastasiyaW @8660456)

- `secret-leak-guard.py`: добавлен allowlist `SAFE_PLACEHOLDER_BASENAMES`
  (placeholder env-files: `.example`/`.sample`/`.template`) в
  `path_is_secret()`. Upstream-регулярка ловит эти файлы, что мешает
  пилоту читать шаблон. Bypass через `CLAUDE_ALLOW_SECRETS=1` запрещён
  политикой (см. `docs/contracts/safety-rules.md` §3.1), поэтому решение —
  точечный allowlist в коде хука. `SECRET_PATH_REGEX` оставлена
  байт-в-байт upstream для упрощения будущего merge.
- `api-key-leak-detector.py`: переписан финальный блок «Action items»
  в stderr-warning'е. Убрана рекомендация `force-push after BFG`
  (противоречит `safety-rules.md` §3 и `git-destructive-guard.py`).
  Теперь рекомендации: ротация секрета у провайдера (см. его docs),
  pre-commit unstage, post-push — обращение к ответственному за
  платформу.
