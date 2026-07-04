.PHONY: help setup wt-new wt-prune preview

# Absolute path of the main worktree (always the first entry in
# `git worktree list --porcelain`, independent of current cwd).
MAIN_TOPLEVEL := $(shell git worktree list --porcelain 2>/dev/null | sed -n 's/^worktree //p' | head -1)
MAIN_REPO_NAME := $(notdir $(MAIN_TOPLEVEL))
# Worktrees live INSIDE the repo (.worktrees/, gitignored): a sibling dir
# would fall outside the project root, which working-directory-guard blocks,
# and outside a Codex workspace, which can't write there.
WT_DIR := $(MAIN_TOPLEVEL)/.worktrees

.DEFAULT_GOAL := help

help:
	@echo "Available targets:"
	@echo "  make setup"
	@echo "      Установить нужные утилиты (gh, gitleaks, jq, gettext) через Homebrew. macOS."
	@echo "  make preview"
	@echo "      Open a local browser preview of app/index.html.tpl with SANDBOX_SLUG substituted."
	@echo "      No Docker required. Usage: make preview or SANDBOX_SLUG=my-slug make preview."
	@echo "  make wt-new SLUG=<feature-slug>"
	@echo "      Create a git worktree at $(WT_DIR)/<slug>/ with branch feature/<slug>."
	@echo "      Slug must match ^[a-z0-9][a-z0-9-]*$$ (lowercase letters, digits, dashes;"
	@echo "      must start with letter or digit)."
	@echo "      Must be run from the main worktree ($(MAIN_TOPLEVEL))."
	@echo "  make wt-prune"
	@echo "      Remove worktrees whose PR was merged: origin branch gone AND a merged"
	@echo "      PR whose head SHA matches the branch tip (confirmed via gh). Clean ones"
	@echo "      are removed and their local branch deleted; worktrees with uncommitted"
	@echo "      changes — or where the merge can't be confirmed — are skipped with a warning."
	@echo "      Must be run from the main worktree ($(MAIN_TOPLEVEL))."

setup:
	@os="$$(uname -s)"; \
	if [ "$$os" != "Darwin" ]; then \
	  echo "make setup ставит утилиты автоматически только на macOS (через Homebrew)."; \
	  echo "На твоей ОС поставь вручную: gh, gitleaks, jq, gettext."; \
	  echo "  Debian/Ubuntu:"; \
	  echo "    jq, gettext-base: sudo apt update && sudo apt install -y jq gettext-base"; \
	  echo "    gh, gitleaks: сначала попробуй apt (sudo apt install -y gh gitleaks — в свежих"; \
	  echo "        Ubuntu они есть в universe); если пакет не нашёлся:"; \
	  echo "        gh — из официального репо cli.github.com"; \
	  echo "        (https://github.com/cli/cli/blob/trunk/docs/install_linux.md),"; \
	  echo "        gitleaks — release-бинарь с https://github.com/gitleaks/gitleaks/releases"; \
	  echo "  Другое: https://cli.github.com  и  https://github.com/gitleaks/gitleaks"; \
	  echo "Потом запусти ./infra/start.sh — он проверит, что всё на месте."; \
	  exit 0; \
	fi; \
	if ! command -v brew >/dev/null 2>&1; then \
	  echo "❌ Нужен Homebrew. Поставь по инструкции с https://brew.sh, потом снова: make setup"; \
	  exit 1; \
	fi; \
	missing=""; \
	command -v gh       >/dev/null 2>&1 || missing="$$missing gh"; \
	command -v gitleaks >/dev/null 2>&1 || missing="$$missing gitleaks"; \
	command -v jq       >/dev/null 2>&1 || missing="$$missing jq"; \
	command -v envsubst >/dev/null 2>&1 || missing="$$missing gettext"; \
	if [ -z "$$missing" ]; then \
	  echo "✓ Всё на месте: gh, gitleaks, jq, envsubst."; \
	else \
	  echo "→ Ставлю через brew:$$missing"; \
	  brew install$$missing || { echo "❌ brew install не удался — поставь вручную:$$missing"; exit 1; }; \
	  case "$$missing" in *gettext*) brew link --force gettext >/dev/null 2>&1 || true ;; esac; \
	  echo "✓ Готово."; \
	fi

preview:
	@if ! command -v envsubst >/dev/null 2>&1; then \
		echo "❌ Нужен envsubst (gettext). Установи: brew install gettext (mac) или apt install gettext (linux)"; \
		exit 1; \
	fi
	@SANDBOX_SLUG="$${SANDBOX_SLUG:-preview}" envsubst '$$SANDBOX_SLUG' < app/index.html.tpl > /tmp/vibecoder-preview.html
	@echo "✓ Открываю /tmp/vibecoder-preview.html в браузере (SANDBOX_SLUG=$${SANDBOX_SLUG:-preview})"
	@if command -v open >/dev/null 2>&1; then \
		open /tmp/vibecoder-preview.html; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open /tmp/vibecoder-preview.html; \
	else \
		echo "Открой вручную: file:///tmp/vibecoder-preview.html"; \
	fi

wt-new:
	@if [ -z "$(MAIN_TOPLEVEL)" ]; then \
	  echo "Error: cannot resolve main worktree. Are you inside a git repo?"; \
	  exit 1; \
	fi
	@if [ "$(CURDIR)" != "$(MAIN_TOPLEVEL)" ]; then \
	  echo "Error: run 'make wt-new' from the main worktree."; \
	  echo "  Main:    $(MAIN_TOPLEVEL)"; \
	  echo "  Current: $(CURDIR)"; \
	  exit 1; \
	fi
	@if [ -z "$(SLUG)" ]; then \
	  echo "Error: SLUG is required."; \
	  echo "Usage: make wt-new SLUG=<feature-slug>"; \
	  exit 1; \
	fi
	@if ! printf '%s' '$(SLUG)' | grep -qE '^[a-z0-9][a-z0-9-]*$$'; then \
	  echo "Error: SLUG must match ^[a-z0-9][a-z0-9-]*$$ (got: '$(SLUG)')."; \
	  exit 1; \
	fi
	@if [ -e '$(WT_DIR)/$(SLUG)' ]; then \
	  echo "Error: $(WT_DIR)/$(SLUG) already exists."; \
	  exit 1; \
	fi
	@mkdir -p '$(WT_DIR)'
	@git worktree add -b 'feature/$(SLUG)' '$(WT_DIR)/$(SLUG)'
	@printf '\nWorktree created: %s/%s\nBranch: feature/%s\nNext: cd %s/%s\n' \
	  '$(WT_DIR)' '$(SLUG)' '$(SLUG)' '$(WT_DIR)' '$(SLUG)'

wt-prune:
	@if [ -z "$(MAIN_TOPLEVEL)" ]; then \
	  echo "Error: cannot resolve main worktree. Are you inside a git repo?"; \
	  exit 1; \
	fi
	@if [ "$(CURDIR)" != "$(MAIN_TOPLEVEL)" ]; then \
	  echo "Error: run 'make wt-prune' from the main worktree."; \
	  echo "  Main:    $(MAIN_TOPLEVEL)"; \
	  echo "  Current: $(CURDIR)"; \
	  exit 1; \
	fi
	@git fetch --prune origin 2>/dev/null || \
	  echo "⚠️  git fetch failed — gone-статус может быть устаревшим, продолжаю с локальными данными."
	@rc=0; tmp=$$(mktemp); git worktree list --porcelain > "$$tmp"; path=; \
	while IFS= read -r line; do \
	  case "$$line" in \
	    "worktree "*) path=$${line#worktree } ;; \
	    "branch refs/heads/"*) \
	      branch=$${line#branch refs/heads/}; \
	      if [ "$$path" != "$(MAIN_TOPLEVEL)" ]; then \
	        track=$$(git for-each-ref --format='%(upstream:track)' "refs/heads/$$branch"); \
	        if [ "$$track" = "[gone]" ]; then \
	          if [ -n "$$(git -C "$$path" status --porcelain)" ]; then \
	            echo "⚠️  skip (uncommitted changes): $$path  [$$branch]"; \
	          elif ! command -v gh >/dev/null 2>&1; then \
	            echo "⚠️  skip (gh не найден, не подтвердить merge — удали вручную, если уверен): $$path  [$$branch]"; \
	          else \
	            tip=$$(git rev-parse "refs/heads/$$branch" 2>/dev/null); \
	            if [ -n "$$tip" ] && gh pr list --head "$$branch" --state merged --json headRefOid --jq '.[].headRefOid' 2>/dev/null | grep -qx "$$tip"; then \
	              echo "🗑️  removing: $$path  [$$branch] (PR merged, origin branch gone)"; \
	              if git worktree remove "$$path"; then git branch -D "$$branch" || rc=1; else rc=1; fi; \
	            else \
	              echo "⚠️  skip (origin-ветка удалена, но merged PR для текущего tip не найден — удали вручную, если уверен): $$path  [$$branch]"; \
	            fi; \
	          fi; \
	        fi; \
	      fi; \
	      path= ;; \
	  esac; \
	done < "$$tmp"; \
	rm -f "$$tmp"; \
	echo "wt-prune: done."; \
	exit $$rc
