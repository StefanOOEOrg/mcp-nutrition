# Changelog

## Unreleased

- Tooling: ruff (`E`, `F`, `I`, `UP`, `B`; line length 100, Python 3.11 target) replaces the previous
  linter; the rule set lives in `pyproject.toml` and CI runs it on every Python version of the matrix.

## 0.1.0 — 2026-10-24

Initial release.

- **Meals:** `meal_log`, `meal_list`, `meal_search`, `meal_update`, `meal_delete` — log a meal with its
  nutrition values (the totals come from mcp-food and use the same field names), list and search days,
  change or delete entries.
- **Water:** `water_log`, `water_list`, `water_delete`.
- **Evaluation:** `day_summary` (one day with targets) and `trend_get` (a range of days, averaged).
- **Goals:** `goals_get`, `goals_set` (calories, macros, fibre, sugar, water; individual goals can be
  removed again).
- Postgres-backed (`nutrition` schema); schema created from `src/schema.sql`, container and backup script
  live in `db/`.
- Local MCP server over stdio; configuration via `.env` (`NUTRITION_DATABASE_URL`,
  `NUTRITION_TIMEZONE`, `LOG_LEVEL`); `.env.example` ships the template.
- CI: pytest against a Postgres service plus a lint step on Python 3.11 and 3.14 — the run fails when
  the database is unreachable instead of silently skipping.
