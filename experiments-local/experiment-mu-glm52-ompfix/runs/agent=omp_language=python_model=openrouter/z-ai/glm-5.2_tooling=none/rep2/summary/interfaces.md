# Interfaces

## HTTP routes

(none) — this is an MCP stdio server, not an HTTP service.

## MCP tools

Registered via `@mcp.tool` on a `FastMCP("brazilian-soccer-mcp")` instance in `server.py`. Each is a thin wrapper delegating to the same-named function in `queries.py`.

| Tool | Parameters | Returns | Delegates to |
|------|-----------|---------|--------------|
| `tool_find_matches` | `team`, `opponent`, `competition`, `season`, `start_date`, `end_date`, `stage`, `limit=50` | `list[dict]` of matches | `queries.find_matches` |
| `tool_head_to_head` | `team_a`, `team_b`, `limit=50` | `dict` (W/L/D + match list + derby name) | `queries.head_to_head` |
| `tool_team_statistics` | `team`, `competition`, `season`, `venue` | `dict` (`TeamRecord.to_dict()`) | `queries.team_statistics` |
| `tool_team_competitions` | `team` | `list[dict]` per-competition records | `queries.team_competitions` |
| `tool_search_players` | `name`, `nationality`, `club`, `position`, `position_group`, `min_overall`, `max_overall`, `sort_by="overall"`, `limit=20` | `list[dict]` of players | `queries.search_players` |
| `tool_top_players_at_club` | `club`, `limit=10` | `list[dict]` | `queries.top_players_at_club` |
| `tool_competition_standings` | `competition`, `season`, `top` | `list[dict]` (`Standing`) | `queries.competition_standings` |
| `tool_competition_champion` | `competition`, `season` | `dict \| None` | `queries.competition_champion` |
| `tool_relegated_teams` | `competition`, `season`, `n=4` | `list[str] \| None` | `queries.relegated_teams` |
| `tool_average_goals` | `competition`, `season` | `dict` (avg goals, home/away/draw rates) | `queries.average_goals` |
| `tool_biggest_wins` | `competition`, `season`, `limit=10` | `list[dict]` | `queries.biggest_wins` |
| `tool_best_team_record` | `competition`, `season`, `venue`, `metric="win_rate"`, `top=5` | `list[dict]` | `queries.best_team_record` |
| `tool_derbies` | `season`, `competition` | `list[dict]` | `queries.derbies` |
| `tool_data_summary` | (none) | `dict` inventory | `queries.data_summary` |

## MCP resources

| URI | Returns | Handler |
|-----|---------|---------|
| `data://summary` | `dict` — match/player counts by source, competition, season | `server.py:summary_resource` → `loader.get_data_summary` |

## CLI commands

| Command | Behavior |
|---------|----------|
| `brazilian-soccer-mcp` | Console script (`pyproject.toml` → `brazilian_soccer.server:main`); calls `mcp.run()` — no subcommands or flags |

## Library API

`brazilian_soccer.queries` exports the 15 query functions listed above; `brazilian_soccer.loader` exports `load_matches()`, `load_players()`, `get_data_summary()`, `clear_cache()`, `DATA_DIR`; `brazilian_soccer.normalize` exports `normalize_team()`, `team_key()`, `derby_name()`.

## Data schemas

No database. Two in-memory pandas DataFrames built from CSVs, plus dataclasses in `models.py`.

**Unified match frame** (`load_matches()`), columns:
`date` (str, ISO `YYYY-MM-DD` or None), `competition` (str, canonical), `season` (int/None), `home_team`, `away_team` (str, normalized display), `home_goal`, `away_goal` (int/None), `round` (str/None), `stage` (str/None), `venue` (str/None), `source` (str, originating CSV), `home_key`, `away_key` (accent-folded match keys), `home_corner`, `away_corner`, `home_shots`, `away_shots`, `home_attack`, `away_attack`, `total_corners` (float/None; only from `BR-Football-Dataset.csv`).

Sources merged: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv`. Deduplicated on `(home_key, away_key, date, home_goal, away_goal)`; rows carrying advanced stats win collisions via a `_richness` score. Rows with a null date are exempt from dedup.

**Player frame** (`load_players()`), from `fifa_data.csv` (read with `utf-8-sig`): `ID`, `Name`, `Age`, `Nationality`, `Overall`, `Potential`, `Club`, `Position`, `Jersey Number`, `Height`, `Weight`, `Value`, `Wage`, ~34 skill columns, plus derived `club_key` and `name_key` (accent-folded).

**Canonical competitions** (`models.COMPETITIONS`): `Brasileirão Série A`, `Brasileirão Série B`, `Brasileirão Série C`, `Copa do Brasil`, `Copa Libertadores`.

**Derby table** (`normalize.DERBIES`): 13 rivalries keyed by `frozenset` of team names (Fla-Flu, Clássico Maior, Gre-Nal, Majestoso, Choque-Rei, Atletiba, Ba-Vi, …).
