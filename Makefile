.PHONY: install test lint typecheck run-api db-init db-init-dryrun db-check db-reset-dryrun validate-registries mcp-smoke hermes-smoke hermes-smoke-apply r108-dry-run-preflight r108-run-hermes r108-inspect-state source-health preview-helpers r109-helper-preflight r109b-dry-run-preflight r109b-run-hermes r109b-inspect-state daily-report-preflight daily-report daily-report-inspect hermes-interactive-preflight hermes-interactive-daily hermes-interactive-copy-prompt report-quality-check report-quality-review daily-report-with-quality model-tier-smoke model-tier-smoke-live daily-report-finalize daily-report-debug

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
