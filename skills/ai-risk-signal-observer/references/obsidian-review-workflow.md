# Obsidian Review Workflow

## Vault Structure

```
AI-Risk-Intelligence/
├── 00_Daily/          # Daily report notes
├── 01_Signals/        # Individual signal notes
├── 02_Candidates/     # Raw item/candidate notes
├── 03_Evidence/       # Evidence/claim notes
├── 04_Sources/        # Source registry notes
├── 05_Risk_Domains/   # Risk domain aggregation
├── 06_Entities/       # Entity notes
├── 07_Runs/           # Source run notes
├── 08_Live_Runs/      # Live research run notes
├── 90_Review_Queue/   # Needs-review and failed-sources
└── 99_Indexes/        # Index notes with counts
```

## Review Queue

Two notes in `90_Review_Queue/`:
- `needs-review.md` — signals and evidence needing human review
- `failed-sources.md` — source runs with error status

## Generated Block Safety

All exported content uses markers:
```
<!-- BEGIN_AUTO_GENERATED: hermes-ai-risk-observer -->
... generated content ...
<!-- END_AUTO_GENERATED: hermes-ai-risk-observer -->
```

Human content outside markers is preserved on re-export.

## Commands

```
owl_obsidian_export(action="export_latest")     # Full export
owl_obsidian_export(action="dry_run")            # Preview only
owl_obsidian_export(action="inspect")            # Inspect vault
owl_obsidian_export(action="open_latest_if_available")  # Open in Finder
```

## Bidirectional Links

Daily notes link to signals, candidates, evidence, and source indexes. Signal notes link to evidence and daily reports. All links use Obsidian wikilinks.
