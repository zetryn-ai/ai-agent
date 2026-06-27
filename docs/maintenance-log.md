# Maintenance Log

Internal, non-roadmap changes (refactors, bug fixes, doc cleanups, tooling
tweaks, etc.). For user-facing release notes see [../CHANGELOG.md](../CHANGELOG.md).
For roadmap-feature design docs see [plans/](plans/).

**Convention:** newest entry on top. Keep rows terse. Only the 5 columns
below are required — add free-form notes under the table if needed.

| Date | Description | Action | Before | After |
|---|---|---|---|---|
| 2026-06-27 | Add strategy catalog `docs/STRATEGIES.md` (shipped + S/A/B/C-tier planned + considered-and-rejected) so future strategy questions have a single answer. Add PL1 (Position Lifecycle Helpers) + S5 (Smart Money Confluence) rows to CAPABILITIES.md roadmap. | add | Strategy decisions scattered across conversation history; no document answering "what's next". | `docs/STRATEGIES.md` is single source of truth; CAPABILITIES.md roadmap lists PL1 and S5 as planned. |
| 2026-06-27 | Documentation layout cleanup — collapse `docs/superpowers/` into `docs/plans/`, introduce this maintenance log for non-roadmap changes, add `docs/plans/README.md` index. | refactor | `docs/superpowers/specs/` held in-flight design docs separately from `docs/plans/` (split, confusing) | Single home for design docs (`docs/plans/`), single home for non-roadmap log entries (this file). `docs/superpowers/` removed. |
