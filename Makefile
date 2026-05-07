.PHONY: install test lint typecheck run-api db-init db-init-dryrun db-check db-reset-dryrun validate-registries mcp-smoke hermes-smoke hermes-smoke-apply r108-dry-run-preflight r108-run-hermes r108-inspect-state source-health preview-helpers r109-helper-preflight r109b-dry-run-preflight r109b-run-hermes r109b-inspect-state daily-report-preflight daily-report daily-report-inspect hermes-interactive-preflight hermes-interactive-daily hermes-interactive-copy-prompt report-quality-check report-quality-review daily-report-with-quality model-tier-smoke model-tier-smoke-live daily-report-finalize daily-report-debug obsidian-export obsidian-export-dry-run obsidian-open-latest daily-report-and-obsidian obsidian-inspect daily-report-and-obsidian-e2e daily-report-live-vault daily-report-live-vault-e2e live-vault-inspect obsidian-open-live-run plugin-install-local plugin-install-local-copy plugin-smoke hermes-plugin-smoke skill-smoke daily-report-plugin daily-report-live-vault-plugin plugin-e2e

PYTHON := .venv/bin/python
RUFF := .venv/bin/ruff
MYPY := .venv/bin/mypy
UVICORN := .venv/bin/uvicorn

# Default dry-run database URL (SQLite, no Docker/Postgres needed)
DRYRUN_DB_URL := sqlite:///./.local/risk_observer_dryrun.db

install:
	python -m venv .venv
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest

lint:
	$(RUFF) check .

typecheck:
	$(MYPY) frontier_ai_risk_observer

run-api:
	$(UVICORN) frontier_ai_risk_observer.api.main:app --host 127.0.0.1 --port 8787 --reload

db-init:
	$(PYTHON) -m frontier_ai_risk_observer.db.init

db-init-dryrun:
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) -m frontier_ai_risk_observer.db.dryrun

db-check:
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) -m frontier_ai_risk_observer.db.check

db-reset-dryrun:
	rm -f .local/risk_observer_dryrun.db .local/risk_observer_dryrun.db-wal .local/risk_observer_dryrun.db-shm
	$(MAKE) db-init-dryrun

validate-registries:
	$(PYTHON) scripts/validate_registries.py

mcp-smoke:
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) -m frontier_ai_risk_observer.mcp.smoke

hermes-smoke:
	$(PYTHON) scripts/hermes_integration_smoke.py --dry-run

hermes-smoke-apply:
	$(PYTHON) scripts/hermes_integration_smoke.py --apply

r108-dry-run-preflight:
	$(MAKE) validate-registries
	$(MAKE) mcp-smoke
	$(MAKE) hermes-smoke
	$(MAKE) db-init-dryrun
	$(MAKE) db-check
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/r108_run_hermes.py --preflight

r108-run-hermes:
	$(MAKE) db-init-dryrun
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/r108_run_hermes.py --run

r108-inspect-state:
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/r108_inspect_state.py

source-health:
	$(PYTHON) scripts/check_source_health.py

preview-helpers:
	$(PYTHON) scripts/preview_discovery_helpers.py

r109-helper-preflight:
	$(MAKE) validate-registries
	$(MAKE) source-health
	$(MAKE) mcp-smoke
	$(MAKE) preview-helpers

r109b-dry-run-preflight:
	$(MAKE) validate-registries
	$(MAKE) source-health
	$(MAKE) preview-helpers
	$(MAKE) r109-helper-preflight
	$(MAKE) mcp-smoke
	$(MAKE) hermes-smoke
	$(MAKE) db-check
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/r109b_run_hermes.py --preflight

r109b-run-hermes:
	$(MAKE) db-init-dryrun
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/r109b_run_hermes.py --run

r109b-inspect-state:
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/r109b_inspect_state.py

daily-report-preflight:
	$(MAKE) validate-registries
	$(MAKE) source-health
	$(MAKE) preview-helpers
	$(MAKE) mcp-smoke
	$(MAKE) hermes-smoke
	$(MAKE) db-init-dryrun
	$(MAKE) db-check
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/daily_report.py --preflight

daily-report:
	$(MAKE) db-init-dryrun
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/daily_report.py --run

daily-report-inspect:
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/inspect_daily_report.py

hermes-interactive-preflight:
	$(MAKE) validate-registries
	$(MAKE) source-health
	$(MAKE) mcp-smoke
	$(MAKE) hermes-smoke
	$(MAKE) db-check
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/hermes_interactive_daily.py --preflight

hermes-interactive-daily:
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/hermes_interactive_daily.py --launch

hermes-interactive-copy-prompt:
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/hermes_interactive_daily.py --copy-prompt-only

report-quality-check:
	$(PYTHON) scripts/check_daily_report_quality.py --latest || $(PYTHON) scripts/check_daily_report_quality.py --report tests/fixtures/reports/good_daily_report.md

report-quality-review:
	@LATEST=$$(ls -td runs/daily/*/ 2>/dev/null | head -1); \
	if [ -n "$$LATEST" ]; then \
		REVIEW_DIR="runs/reviews"; \
		mkdir -p "$$REVIEW_DIR"; \
		$(PYTHON) scripts/check_daily_report_quality.py --latest --write-review "$$REVIEW_DIR/review_$$(date +%Y%m%d_%H%M%S).md"; \
	else \
		echo "No daily report found. Using fixture."; \
		mkdir -p runs/reviews; \
		$(PYTHON) scripts/check_daily_report_quality.py --report tests/fixtures/reports/good_daily_report.md --write-review runs/reviews/fixture_review.md; \
	fi

daily-report-with-quality:
	$(MAKE) daily-report
	$(MAKE) report-quality-check

daily-report-finalize:
	@LATEST=$$(ls -td runs/daily/*/ 2>/dev/null | head -1); \
	if [ -n "$$LATEST" ]; then \
		DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/daily_report.py --run --force-finalize --prompt-file "$$LATEST/prompt.md"; \
	else \
		echo "No existing daily report run found. Run make daily-report first."; \
	fi

daily-report-debug:
	@LATEST=$$(ls -td runs/daily/*/ 2>/dev/null | head -1); \
	if [ -n "$$LATEST" ]; then \
		echo "=== Latest daily report run: $$LATEST ==="; \
		if [ -f "$$LATEST/summary.md" ]; then cat "$$LATEST/summary.md"; fi; \
		echo ""; \
		echo "=== Artifacts ==="; \
		ls -la "$$LATEST"; \
	else \
		echo "No daily report run found."; \
	fi

model-tier-smoke:
	@echo "=== Model-Tier Smoke Test (no network, no API keys) ==="
	$(PYTHON) -c "from frontier_ai_risk_observer.models.config import SmallModelConfig; \
	from frontier_ai_risk_observer.services.candidate_preprocess import preprocess_candidate; \
	config = SmallModelConfig(enabled=False); \
	result = preprocess_candidate(title='Smoke test', config=config); \
	assert result.advisory_only is True; \
	print('OK: deterministic fallback works')"
	@echo "=== Model-Tier Smoke: PASSED ==="

model-tier-smoke-live:
	@echo "=== Model-Tier Smoke Test (live, requires configuration) ==="
	$(PYTHON) -c "from frontier_ai_risk_observer.models.config import load_small_model_config; \
	from frontier_ai_risk_observer.services.candidate_preprocess import preprocess_candidate; \
	config = load_small_model_config(); \
	assert config.enabled, 'Small model not enabled. Set AIRO_ENABLE_SMALL_MODEL=true'; \
	result = preprocess_candidate(title='Live smoke test', content_text='AI safety regulation update', config=config); \
	assert result.advisory_only is True; \
	print(f'OK: small model={result.model_used}, advisory_only={result.advisory_only}')"

obsidian-export:
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/obsidian_export.py --latest

obsidian-export-dry-run:
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/obsidian_export.py --latest --dry-run

obsidian-open-latest:
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/obsidian_export.py --latest --open

daily-report-and-obsidian:
	$(MAKE) daily-report
	$(MAKE) obsidian-export

obsidian-inspect:
	$(PYTHON) scripts/inspect_obsidian_export.py --vault $${OBSIDIAN_VAULT_PATH:-.local/obsidian_vault}

daily-report-and-obsidian-e2e:
	@if [ -z "$$OBSIDIAN_VAULT_PATH" ]; then \
		echo "ERROR: OBSIDIAN_VAULT_PATH is not set."; \
		echo "Set it before running, e.g.:"; \
		echo "  OBSIDIAN_VAULT_PATH=.local/obsidian_e2e_vault make daily-report-and-obsidian-e2e"; \
		exit 1; \
	fi
	$(MAKE) daily-report
	$(MAKE) report-quality-check
	$(MAKE) obsidian-export
	$(MAKE) obsidian-inspect

daily-report-live-vault:
	@if [ -z "$$OBSIDIAN_VAULT_PATH" ]; then \
		echo "ERROR: OBSIDIAN_VAULT_PATH is not set."; \
		echo "Set it before running, e.g.:"; \
		echo "  OBSIDIAN_VAULT_PATH=~/Documents/airo make daily-report-live-vault"; \
		exit 1; \
	fi
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/daily_report.py --run --live-vault
	$(MAKE) report-quality-check
	$(MAKE) live-vault-inspect

live-vault-inspect:
	$(PYTHON) scripts/inspect_live_vault.py --vault $${OBSIDIAN_VAULT_PATH:-.local/obsidian_vault}

obsidian-open-live-run:
	@VAULT=$${OBSIDIAN_VAULT_PATH:-.local/obsidian_vault}; \
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) -c \
	"from frontier_ai_risk_observer.obsidian.cli import open_live_run; from pathlib import Path; \
	success = open_live_run(Path('$$VAULT')); \
	print('Opened live run' if success else 'No live run found or Obsidian not available')"

daily-report-live-vault-e2e:
	@if [ -z "$$OBSIDIAN_VAULT_PATH" ]; then \
		echo "ERROR: OBSIDIAN_VAULT_PATH is not set."; \
		echo "Set it before running, e.g.:"; \
		echo "  OBSIDIAN_VAULT_PATH=~/Documents/airo make daily-report-live-vault-e2e"; \
		exit 1; \
	fi
	@echo "=== R1-13C: Live Vault E2E Validation ==="
	OBSIDIAN_LIVE_LOGGING_ENABLED=true DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/daily_report.py --run --live-vault
	$(MAKE) report-quality-check
	@echo "=== Inspecting live vault (with requirements) ==="
	$(PYTHON) scripts/inspect_live_vault.py --vault $${OBSIDIAN_VAULT_PATH} --latest --require-events 1 --require-note-types source,candidate,evidence,signal --require-daily-note --require-daily-body --db-check
	@echo "=== Inspecting Obsidian vault ==="
	$(MAKE) obsidian-inspect
	@echo "=== R1-13C: E2E Validation Complete ==="

# R1-15: Plugin + Bundled Skills Migration

plugin-install-local:
	$(PYTHON) scripts/install_hermes_plugin.py --mode symlink

plugin-install-local-copy:
	$(PYTHON) scripts/install_hermes_plugin.py --mode copy

plugin-smoke:
	$(PYTHON) scripts/plugin_smoke.py

hermes-plugin-smoke:
	$(PYTHON) scripts/hermes_plugin_smoke.py

skill-smoke:
	$(PYTHON) scripts/skill_smoke.py

daily-report-plugin:
	DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/daily_report.py --run --interface plugin

daily-report-live-vault-plugin:
	@if [ -z "$$OBSIDIAN_VAULT_PATH" ]; then \
		echo "ERROR: OBSIDIAN_VAULT_PATH is not set."; \
		echo "Set it before running, e.g.:"; \
		echo "  OBSIDIAN_VAULT_PATH=~/Documents/airo make daily-report-live-vault-plugin"; \
		exit 1; \
	fi
	OBSIDIAN_LIVE_LOGGING_ENABLED=true DATABASE_URL="$(DRYRUN_DB_URL)" $(PYTHON) scripts/daily_report.py --run --live-vault --interface plugin

plugin-e2e:
	@echo "=== R1-15: Plugin E2E Validation ==="
	$(MAKE) plugin-smoke
	$(MAKE) skill-smoke
	$(MAKE) hermes-plugin-smoke
	$(MAKE) mcp-smoke
	@echo "=== Plugin E2E smoke passed ==="
	@if [ -n "$$OBSIDIAN_VAULT_PATH" ]; then \
		echo "OBSIDIAN_VAULT_PATH set — running daily-report-plugin..."; \
		$(MAKE) daily-report-plugin; \
	else \
		echo "OBSIDIAN_VAULT_PATH not set — skipping live daily report."; \
	fi
	@echo "=== R1-15: Plugin E2E Complete ==="
