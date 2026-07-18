# Summary: agent=omp · language=python · model=openrouter/z-ai/glm-5.2 · tooling=none · rep 2

- **Shape:** Incomplete — a pandas-backed data/query library for the Brazilian soccer MCP
  task, with the MCP server layer never written. Layered as
  `normalize → loader (pandas + lru_cache) → queries`, all returning plain JSON-serializable
  dicts intended for an MCP tool layer that does not exist on disk.
- **Structure:** 4 modules (`loader.py` 357, `models.py` 147, `normalize.py` 135,
  `queries.py` 539 lines), **0 test files**. No `server.py`, no `tests/`, no
  `__init__.py`. `pyproject.toml` still declares `brazilian_soccer.server:main` as its
  console script and `testpaths = ["tests"]`, and depends on `mcp`/`fastmcp` — nothing
  imports either. The run aborted mid-way.
- **Interfaces:** 0 HTTP routes / 0 MCP tools / 0 CLI commands / 14 public query functions
  (+ 5 loader and 3 normalize exports) across all five TASK.md query categories: match,
  team, player, competition, statistical.
- **Notable:** The data layer is the most developed part — it unifies all six CSVs
  (differing column names, ISO vs day-first dates, string-typed goals) and deduplicates the
  deliberately overlapping sources on `(home_key, away_key, date, goals)` using a
  "richness" score so stats-carrying rows survive the merge. Team-name normalization is
  handled with a dedicated module (state-suffix stripping validated against the 27 UF codes
  plus 9 foreign codes, parenthetical stripping, NFKD accent folding) and a hardcoded
  13-entry derby table. Against that, the query layer carries visible unfinished edges:
  a duplicate `_STATE_SUFFIX` compile, an `if False` no-op and an unused variable in
  `best_team_record`, a doubly-applied filter in `derbies`, and a `Player` dataclass that
  is never constructed.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
