You are working in the repository for the Hermes-Agent based Frontier AI Risk Observer / OwlHermes.

The product owner has decided to perform a full architecture refactor.

We are no longer doing a small plugin scaffold only.

We are now moving OwlHermes to a **Hermes Plugin + Bundled Skills primary architecture**.

Current architecture:

- OwlHermes currently exposes many `risk_*` MCP tools.
- SQLite stores deterministic runtime state:
  - registry;
  - raw items;
  - source runs;
  - evidence;
  - signals;
  - digests;
  - research events.
- Obsidian Vault stores human-facing research notes:
  - daily report notes;
  - signal notes;
  - candidate notes;
  - evidence notes;
  - source notes;
  - live research logs.
- Skills contain workflow instructions.
- MCP currently acts as the main Hermes integration surface.

Target architecture:

- Hermes Plugin is the primary integration surface.
- Bundled Skills are the primary workflow / policy / editorial knowledge surface.
- SQLite remains the deterministic runtime state layer.
- Obsidian remains the human-facing live research workspace and intelligence vault.
- MCP becomes legacy fallback / compatibility only.
- Daily report and live vault workflows should prefer plugin tools, not MCP tools.

Important Hermes facts to respect:

- Hermes plugins can add tools, hooks, slash commands, CLI commands, shipped data files, and bundled skills through `register(ctx)`.
- Plugins can register tools with `ctx.register_tool(...)`.
- Plugins can register bundled skills with `ctx.register_skill(name, path)`.
- Plugins can register CLI commands with `ctx.register_cli_command(...)`.
- User plugins can live under `~/.hermes/plugins/<plugin-name>/`.
- Project plugins under `./.hermes/plugins/` require `HERMES_ENABLE_PROJECT_PLUGINS=true`.
- General plugins are opt-in and must be enabled in `~/.hermes/config.yaml` under `plugins.enabled`.
- For custom tool creation, Hermes docs recommend starting with plugins rather than modifying Hermes core tools.

R1-15 goal:

Implement **R1-15: Full Hermes Plugin + Bundled Skills Migration**.

This is a comprehensive migration.

By the end, OwlHermes should be usable primarily as a Hermes plugin with bundled skills.

The preferred user path should become:

```bash
make plugin-install-local
make hermes-plugin-smoke
make daily-report-plugin
make daily-report-live-vault-plugin
````

Existing MCP workflows should still be available as legacy fallback, but should no longer be the recommended path.

Core success criteria:

1. A real Hermes plugin package exists.
2. Plugin metadata exists.
3. Plugin registers OwlHermes tools.
4. Plugin bundles OwlHermes skills.
5. Plugin exposes high-level facade tools, not dozens of tiny tools.
6. Daily report prompts prefer plugin tools.
7. Live Obsidian vault prompts prefer plugin tools.
8. MCP compatibility remains available but is documented as legacy.
9. `make daily-report-plugin` can run the daily report flow through plugin-preferred prompts/config.
10. `make daily-report-live-vault-plugin` can run live vault daily flow through plugin-preferred prompts/config.
11. Existing `make daily-report`, `make daily-report-live-vault`, `make obsidian-export`, and MCP smoke tests do not break.

Non-negotiable constraints:

* Do not remove SQLite.
* Do not remove Obsidian.
* Do not remove existing backend services.
* Do not remove MCP in this round.
* Do not remove current tests.
* Do not break the reliable two-phase daily report flow.
* Do not break live Obsidian research logging.
* Do not require Docker.
* Do not require Postgres.
* Do not require Obsidian CLI.
* Do not require Obsidian app for tests.
* Do not require network in default tests.
* Do not configure delivery channels.
* Do not post externally.
* Do not run production cron.
* Do not expose arbitrary filesystem writes.
* Do not write private chain-of-thought into Obsidian.
* Do not replace Hermes risk judgment with Python templates.
* Default validation must remain offline.

First, read these files carefully:

* README.md
* CLAUDE.md
* Makefile
* pyproject.toml
* configs/env.example
* configs/hermes_config.example.yaml
* source_registry/sources.yaml
* source_registry/podcasts.yaml
* skills/ai-risk-signal-observer/SKILL.md
* prompts/daily_report_prompt.md
* prompts/daily_report_finalize_prompt.md
* prompts/interactive_daily_report_prompt.md
* frontier_ai_risk_observer/mcp/server.py
* frontier_ai_risk_observer/mcp/schemas.py
* frontier_ai_risk_observer/services/ingestion.py
* frontier_ai_risk_observer/services/signals.py
* frontier_ai_risk_observer/services/evidence.py
* frontier_ai_risk_observer/services/digest.py
* frontier_ai_risk_observer/services/live_research.py
* frontier_ai_risk_observer/services/source_health.py
* frontier_ai_risk_observer/services/registry_service.py
* frontier_ai_risk_observer/obsidian/live_writer.py
* frontier_ai_risk_observer/obsidian/daily_note.py if present
* frontier_ai_risk_observer/obsidian/exporter.py
* frontier_ai_risk_observer/obsidian/markdown.py
* frontier_ai_risk_observer/quality/report_quality.py
* scripts/daily_report.py
* scripts/obsidian_export.py
* scripts/check_daily_report_quality.py
* scripts/inspect_live_vault.py
* docs/21_daily_report_quality_rubric.md
* docs/23_obsidian_intelligence_vault.md
* docs/24_live_obsidian_research_logging.md
* docs/25_source_reliability_patch.md if present
* tests/

Required work:

1. Verify Hermes plugin API locally.

   Do not guess.

   Inspect installed Hermes package if available.

   Run or inspect:

   * `hermes --help`
   * `hermes plugins --help`
   * Hermes plugin docs available locally if any
   * installed Python package symbols if available

   Confirm:

   * plugin directory structure;
   * plugin manifest fields;
   * `register(ctx)` API;
   * `ctx.register_tool`;
   * `ctx.register_skill`;
   * `ctx.register_cli_command`;
   * how plugins are enabled;
   * how project-local plugins are enabled;
   * how tool schemas are represented;
   * how handler return values should be formatted.

   Add documentation:

   * `docs/28_hermes_plugin_api_findings.md`

   It should include:

   * exact API found;
   * exact plugin file layout chosen;
   * exact enable/install flow;
   * uncertainties;
   * what is confirmed vs inferred.

   If Hermes plugin runtime cannot be imported or tested:

   * still implement the plugin package;
   * make smoke tests validate import/manifest/tool registry;
   * mark real Hermes plugin loading as pending;
   * do not claim full runtime success.

2. Create canonical plugin source package.

   Add package:

   ```text
   frontier_ai_risk_observer/hermes_plugin/
     __init__.py
     plugin.py
     tools.py
     schemas.py
     facades.py
     hooks.py
     cli_commands.py
     skills.py
     manifest.py
     README.md
   ```

   Responsibilities:

   * `plugin.py`

     * defines `register(ctx)`;
     * registers tools;
     * registers bundled skills;
     * optionally registers CLI commands;
     * optionally registers hooks.

   * `tools.py`

     * contains plugin tool handlers;
     * calls facade functions;
     * returns JSON-compatible dicts or JSON strings depending on Hermes API.

   * `schemas.py`

     * contains plugin tool schemas in the exact format Hermes expects.

   * `facades.py`

     * implements high-level tool action routing;
     * reuses existing services.

   * `hooks.py`

     * optional hooks, initially minimal/no-op;
     * do not add noisy logging.

   * `cli_commands.py`

     * plugin CLI command handlers if supported.

   * `skills.py`

     * registers bundled skill paths.

   * `manifest.py`

     * Python representation of plugin metadata if useful.

3. Add plugin distribution directory.

   Add a Hermes drop-in plugin directory in the repo:

   ```text
   .hermes/plugins/owlhermes/
     plugin.yaml
     __init__.py
     schemas.py
     tools.py
     skills/
       ai-risk-signal-observer/
         SKILL.md
         references/...
   ```

   This directory should be installable or symlinkable into `~/.hermes/plugins/owlhermes`.

   Important:

   * Do not duplicate large business logic in `.hermes/plugins`.
   * The plugin files there should import from `frontier_ai_risk_observer.hermes_plugin`.
   * Keep `.hermes/plugins/owlhermes` thin.
   * Include clear comments that project plugins require `HERMES_ENABLE_PROJECT_PLUGINS=true`.

4. Add plugin manifest.

   Create:

   * `.hermes/plugins/owlhermes/plugin.yaml`

   Include at least:

   ```yaml
   name: owlhermes
   version: "0.1.0"
   description: Hermes-native Frontier AI Risk Intelligence Observer
   provides_tools:
     - owl_risk_state
     - owl_risk_discovery
     - owl_live_vault
     - owl_report_quality
     - owl_obsidian_export
   provides_hooks: []
   ```

   Add env documentation in comments or README:

   * `DATABASE_URL`
   * `SOURCE_REGISTRY_DIR`
   * `OBSIDIAN_VAULT_PATH`
   * `OBSIDIAN_LIVE_LOGGING_ENABLED`
   * `OBSIDIAN_LIVE_APPEND_TO_DAILY`
   * `AIRO_ENABLE_SMALL_MODEL` if relevant

   Do not include secrets.

5. Implement plugin facade tools.

   Add these plugin tools as the preferred surface:

   A. `owl_risk_state`

   Purpose:

   Deterministic state operations.

   Actions:

   * `seen_check`
   * `store_raw_item`
   * `search_raw_items`
   * `duplicate_candidates`
   * `record_source_run`
   * `store_evidence`
   * `search_evidence`
   * `store_signal`
   * `search_signals`
   * `store_digest`
   * `search_digests`

   B. `owl_risk_discovery`

   Purpose:

   Source registry and discovery helper operations.

   Actions:

   * `registry_summary`
   * `list_due_sources`
   * `get_source`
   * `source_health`
   * `helper_preview`
   * `feed_preview`
   * `sitemap_preview`
   * `source_policy_summary`

   C. `owl_live_vault`

   Purpose:

   Live Obsidian research logging.

   Actions:

   * `start_run`
   * `append_event`
   * `upsert_note`
   * `upsert_daily_report`
   * `finalize_run`
   * `inspect_latest`

   D. `owl_report_quality`

   Purpose:

   Report quality and review.

   Actions:

   * `check_report`
   * `latest_report_summary`
   * `review_queue_summary`
   * `quality_rubric_summary`

   E. `owl_obsidian_export`

   Purpose:

   Obsidian vault export/backfill.

   Actions:

   * `export_latest`
   * `dry_run`
   * `inspect`
   * `open_latest_if_available`

   Tool requirements:

   * Validate action names.
   * Validate payloads.
   * Return JSON-compatible dicts.
   * Do not expose arbitrary file paths.
   * Do not allow writes outside configured vault.
   * Preserve human content outside generated blocks.
   * Never write private chain-of-thought.
   * Do not require network by default.
   * Do not require Obsidian CLI.
   * Gracefully report disabled live vault.
   * Reuse existing service functions and MCP handler logic where possible.
   * Do not duplicate business logic.

6. Preserve legacy MCP but demote it.

   Keep existing MCP server and all legacy tools.

   Add env/config:

   * `OWL_HERMES_INTERFACE_MODE`

     * allowed:

       * `plugin`
       * `mcp`
       * `both`
     * default: `both` for transition.

   Update docs and config so:

   * plugin mode is preferred;
   * MCP mode is legacy fallback;
   * existing automation can still use MCP until plugin E2E is stable.

   Do not delete MCP tools in this round.

7. Split and bundle skills.

   Refactor:

   ```text
   skills/ai-risk-signal-observer/
     SKILL.md
     references/
       source-policy.md
       signal-rubric.md
       evidence-policy.md
       live-vault-workflow.md
       final-report-format.md
       obsidian-review-workflow.md
       plugin-tool-guide.md
       mcp-legacy-guide.md
       source-reliability-known-issues.md
   ```

   Main `SKILL.md` should be short and orchestrating.

   It should say:

   * You are OwlHermes, a Hermes-native AI risk intelligence observer.
   * Prefer plugin tools:

     * `owl_risk_discovery`
     * `owl_risk_state`
     * `owl_live_vault`
     * `owl_report_quality`
     * `owl_obsidian_export`
   * Use legacy MCP tools only if plugin tools are unavailable.
   * Load reference files as needed:

     * source policy;
     * signal rubric;
     * evidence policy;
     * live vault workflow;
     * report format;
     * plugin tool guide.

   Reference files must include:

   * source reliability policy:

     * no Cloudflare/CAPTCHA bypass;
     * feed/sitemap/list page first;
     * known broken sources;
     * search fallback only when allowed.

   * signal rubric:

     * what changed;
     * why it matters;
     * what to watch next;
     * candidate vs signal;
     * no news dump.

   * evidence policy:

     * evidence URL;
     * evidence excerpt;
     * claim text;
     * needs review if missing.

   * live vault workflow:

     * write source/candidate/evidence/signal/failure notes live;
     * write final daily note immediately;
     * bidirectional links;
     * no private chain-of-thought.

   * final report format:

     * Chinese report;
     * concise;
     * evidence-backed;
     * source coverage;
     * uncertainty;
     * follow-up.

   * plugin tool guide:

     * action-by-action mapping.

   Bundle these skills into `.hermes/plugins/owlhermes/skills/`.

8. Update prompts to plugin-first.

   Update:

   * `prompts/daily_report_prompt.md`
   * `prompts/daily_report_finalize_prompt.md`
   * `prompts/interactive_daily_report_prompt.md`

   Replace long legacy MCP tool lists with plugin-first tool usage.

   Example guidance:

   * Start live run:

     * `owl_live_vault(action="start_run", payload={...})`

   * Source health:

     * `owl_risk_discovery(action="source_health", payload={...})`

   * Due sources:

     * `owl_risk_discovery(action="list_due_sources", payload={...})`

   * Helper preview:

     * `owl_risk_discovery(action="helper_preview", payload={...})`

   * Seen check:

     * `owl_risk_state(action="seen_check", payload={...})`

   * Store candidate:

     * `owl_risk_state(action="store_raw_item", payload={...})`

   * Store evidence:

     * `owl_risk_state(action="store_evidence", payload={...})`

   * Store signal:

     * `owl_risk_state(action="store_signal", payload={...})`

   * Store digest:

     * `owl_risk_state(action="store_digest", payload={...})`

   * Live note:

     * `owl_live_vault(action="upsert_note", payload={...})`

   * Live daily report:

     * `owl_live_vault(action="upsert_daily_report", payload={...})`

   * Finalize:

     * `owl_live_vault(action="finalize_run", payload={...})`

   * Quality check:

     * `owl_report_quality(action="check_report", payload={...})`

   Add fallback note:

   * If OwlHermes plugin tools are unavailable, use MCP legacy tools with equivalent semantics.

   Maintain all behavioral rules:

   * no private chain-of-thought;
   * no external posting;
   * no anti-bot bypass;
   * seen-check before store;
   * evidence before signal when possible;
   * final daily report written to Obsidian immediately when live vault enabled.

9. Add plugin install helpers.

   Add scripts:

   * `scripts/install_hermes_plugin.py`
   * `scripts/plugin_smoke.py`
   * `scripts/hermes_plugin_smoke.py`
   * `scripts/skill_smoke.py`

   `install_hermes_plugin.py` should:

   * support:

     * `--mode symlink`
     * `--mode copy`
     * `--target ~/.hermes/plugins/owlhermes`
     * `--project-local`
     * `--dry-run`
   * symlink or copy `.hermes/plugins/owlhermes` into `~/.hermes/plugins/owlhermes`;
   * never overwrite without backup or explicit flag;
   * print next steps:

     * enable plugin in `~/.hermes/config.yaml`;
     * run `hermes plugins enable owlhermes`;
     * set env vars.

   `plugin_smoke.py` should:

   * import plugin package;
   * inspect manifest;
   * list plugin tools;
   * run no-network tool smoke calls;
   * work without Hermes runtime.

   `hermes_plugin_smoke.py` should:

   * check whether Hermes CLI exists;
   * check whether plugin path exists;
   * attempt safe plugin discovery if supported;
   * report:

     * hermes_available;
     * plugin_installed;
     * plugin_enabled;
     * plugin_tools_discovered;
   * if runtime discovery cannot be automated, report pending clearly.
   * Do not fake success.

   `skill_smoke.py` should:

   * validate skill files;
   * validate references;
   * validate plugin-first language;
   * validate MCP fallback language.

10. Add Makefile targets.

Add:

* `make plugin-install-local`
* `make plugin-install-local-copy`
* `make plugin-smoke`
* `make hermes-plugin-smoke`
* `make skill-smoke`
* `make daily-report-plugin`
* `make daily-report-live-vault-plugin`
* `make plugin-e2e`

Behavior:

`make plugin-install-local`:

* symlink local plugin into `~/.hermes/plugins/owlhermes`.

`make plugin-smoke`:

* runs plugin import/manifest/tool smoke without Hermes.

`make hermes-plugin-smoke`:

* checks Hermes discovery/enabled status if possible.

`make skill-smoke`:

* validates bundled skills.

`make daily-report-plugin`:

* runs daily report with plugin-first prompt/config.
* does not require MCP except fallback.

`make daily-report-live-vault-plugin`:

* runs daily report with live vault and plugin-first prompt/config.

`make plugin-e2e`:

* runs:

  * plugin-smoke;
  * skill-smoke;
  * hermes-plugin-smoke;
  * daily-report-plugin if safe;
  * optionally live-vault plugin flow if `OBSIDIAN_VAULT_PATH` set.

Do not make plugin E2E require network by default unless it already does because Hermes browses.

11. Update Hermes config examples.

Update:

* `configs/hermes_config.example.yaml`

Add plugin-first configuration.

Include:

```yaml
plugins:
  enabled:
    - owlhermes
```

Include comments for env:

* `DATABASE_URL`
* `SOURCE_REGISTRY_DIR`
* `OBSIDIAN_VAULT_PATH`
* `OBSIDIAN_LIVE_LOGGING_ENABLED`

Keep MCP compatibility configuration in a separate section:

* “Legacy MCP fallback”.

Make it clear:

* plugin-first is recommended;
* MCP is fallback/debug.

12. Update daily report runner.

Update:

* `scripts/daily_report.py`

Add option:

* `--interface plugin`
* `--interface mcp`
* `--interface auto`

Default for new plugin targets:

* `plugin`

Default for old targets:

* keep existing behavior or `auto`, but do not break.

Behavior:

* plugin mode uses plugin-first prompt.
* MCP mode uses MCP-compatible prompt.
* auto mode says plugin preferred, MCP fallback.

Summary should record:

* interface_mode;
* plugin_tools_expected;
* mcp_fallback_allowed;
* plugin_smoke_status if available.

13. Add plugin-first prompt files if cleaner.

If modifying existing prompts is risky, add:

* `prompts/daily_report_plugin_prompt.md`
* `prompts/daily_report_plugin_finalize_prompt.md`
* `prompts/interactive_daily_report_plugin_prompt.md`

These should be the preferred new prompts.

Old prompts can remain for MCP compatibility.

14. Update docs.

Add:

* `docs/27_full_plugin_skills_migration.md`

It must explain:

* why full migration is happening;
* why plugin + skills, not pure skills;
* what plugin tools do;
* what skills do;
* why SQLite remains;
* why Obsidian remains;
* why MCP remains temporarily;
* how to install plugin;
* how to enable plugin;
* how to run smoke tests;
* how to run plugin daily report;
* how to debug fallback.

Add:

* `docs/28_plugin_installation_debugging.md`

It must include:

* local symlink install;
* copy install;
* project-local plugin mode;
* `HERMES_ENABLE_PROJECT_PLUGINS=true`;
* enabling in `~/.hermes/config.yaml`;
* common failure modes;
* how to confirm tools are visible;
* how to fall back to MCP.

Update:

* README.md
* CLAUDE.md
* docs/23_obsidian_intelligence_vault.md
* docs/24_live_obsidian_research_logging.md
* docs/25_source_reliability_patch.md if present.

15. Add tests.

Tests must not require:

* Hermes runtime;
* Docker;
* Postgres;
* Obsidian CLI;
* network.

Add tests for:

Plugin package:

* `frontier_ai_risk_observer.hermes_plugin` imports.
* `register(ctx)` exists.
* plugin manifest exists.
* plugin tools list includes all expected tools.
* plugin schemas validate.
* invalid tool action fails cleanly.
* plugin tools return JSON-compatible data.
* plugin tools do not allow arbitrary file writes.
* live vault disabled returns disabled status.

Plugin install script:

* dry-run works.
* symlink target path computed correctly.
* copy mode does not overwrite without explicit flag.
* project-local mode documented.

Facade tools:

* `owl_risk_discovery` source_health works offline.
* `owl_risk_state` seen_check works with SQLite test DB or controlled unavailable response.
* `owl_live_vault` disabled works.
* `owl_report_quality` graceful missing report.
* `owl_obsidian_export` dry-run works.

Skills:

* main skill exists.
* references exist.
* source-policy mentions no anti-bot bypass.
* signal-rubric mentions what changed / why / watch next.
* evidence-policy mentions evidence excerpts.
* live-vault-workflow mentions intermediate notes and daily note immediate write.
* plugin-tool-guide maps plugin actions.
* mcp-legacy-guide exists.

Prompts:

* plugin prompts prefer `owl_*` tools.
* plugin prompts mention MCP fallback.
* prompts forbid private chain-of-thought logging.
* prompts say final daily note must be written immediately.

Config/docs:

* Hermes config example has plugin-enabled mode.
* MCP fallback still documented.
* README mentions plugin-first architecture.

Smoke scripts:

* plugin_smoke works without Hermes.
* skill_smoke works.
* hermes_plugin_smoke reports unavailable/pending cleanly if Hermes cannot load plugin.

16. Run validation commands.

Run at minimum:

```bash
make validate-registries
make source-health
make db-check
make plugin-smoke
make skill-smoke
make hermes-plugin-smoke
make mcp-smoke
make test
make lint
make typecheck
python -m compileall frontier_ai_risk_observer tests scripts
```

If safe:

```bash
make plugin-install-local
make hermes-plugin-smoke
```

If Hermes plugin discovery works:

```bash
make daily-report-plugin
```

If `OBSIDIAN_VAULT_PATH` is set and safe:

```bash
OBSIDIAN_LIVE_LOGGING_ENABLED=true make daily-report-live-vault-plugin
```

17. Do not fake success.

If Hermes plugin runtime cannot load the plugin:

* report exactly what failed;
* keep plugin package and smoke tests passing;
* document runtime blocker;
* recommend R1-15B plugin runtime repair.

Do not claim plugin E2E works unless Hermes actually discovers and can call plugin tools.

18. Report results.

When finished, report:

1. Files created or changed.
2. Commands run and whether they passed.
3. Whether full plugin package exists.
4. Plugin directory path.
5. Plugin manifest path.
6. Plugin tools implemented.
7. Bundled skills implemented.
8. Skill references created.
9. Whether plugin install works.
10. Whether Hermes discovers plugin.
11. Whether Hermes can see plugin tools.
12. Whether plugin daily report was run.
13. Whether plugin live-vault daily report was run.
14. Whether MCP fallback remains.
15. Whether existing MCP workflows still pass.
16. Whether SQLite and Obsidian remain intact.
17. Whether no private chain-of-thought is written.
18. Whether default tests remain offline.
19. Any runtime plugin blockers.
20. Recommended next task:

    * R1-15B Hermes Plugin Runtime E2E Repair if discovery/loading failed;
    * R1-16 Source Reliability Patch if plugin migration works;
    * R1-16 Obsidian Review Sync if plugin migration and live vault are stable.