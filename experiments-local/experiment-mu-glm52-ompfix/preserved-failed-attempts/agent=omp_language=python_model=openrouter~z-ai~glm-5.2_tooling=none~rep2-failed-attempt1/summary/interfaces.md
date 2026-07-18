# Interfaces

## HTTP routes

(none)

## MCP tools

(none) — `server.py` is absent from the archive. `pyproject.toml` declares the console
script `brazilian-soccer-mcp = "brazilian_soccer.server:main"` and depends on `mcp>=1.0`
and `fastmcp>=2.0`, but no module registers any MCP tool. No `@mcp.tool`, `FastMCP`, or
`Server` declaration exists on disk.

## CLI commands

(none) — the only declared entry point is the console script above, whose target module
does not exist.

## Library API

The package is importable only as loose modules (`brazilian_soccer/__init__.py` is absent).
All functions below return plain `dict` / `list[dict]` — the header comments state this is
so the MCP layer can return them verbatim as structured output.

### `queries` — match queries

| Function | Signature (defaults) | Returns |
|----------|----------------------|---------|
| `find_matches` | `team=None, opponent=None, competition=None, season=None, start_date=None, end_date=None, stage=None, limit=50` | `list[dict]` match rows, date-descending |
| `head_to_head` | `team_a, team_b, limit=50` | `dict` with `derby`, `matches_found`, `team_a_wins`, `team_b_wins`, `draws`, `matches` |

### `queries` — team queries

| Function | Signature (defaults) | Returns |
|----------|----------------------|---------|
| `team_statistics` | `team, competition=None, season=None, venue=None` (`venue` ∈ `"home"`/`"away"`/`None`) | `TeamRecord.to_dict()` |
| `team_competitions` | `team` | `list[dict]` — one record per competition, plus `seasons` |

### `queries` — player queries

| Function | Signature (defaults) | Returns |
|----------|----------------------|---------|
| `search_players` | `name=None, nationality=None, club=None, position=None, position_group=None, min_overall=None, max_overall=None, sort_by="overall", limit=20` | `list[dict]` player rows |
| `top_players_at_club` | `club, limit=10` | `list[dict]` (delegates to `search_players`) |

### `queries` — competition queries

| Function | Signature (defaults) | Returns |
|----------|----------------------|---------|
| `competition_standings` | `competition, season, top=None` | `list[dict]` — `Standing` rows, 3pt/win, ties by GD then GF then name |
| `competition_champion` | `competition, season` | `dict \| None` |
| `relegated_teams` | `competition, season, n=4` | `list[str] \| None` (bottom-n; `None` if table shorter than `n`) |

### `queries` — statistical analysis

| Function | Signature (defaults) | Returns |
|----------|----------------------|---------|
| `average_goals` | `competition=None, season=None` | `dict`: `matches`, `total_goals`, `avg_goals_per_match`, home/away/draw counts + rates |
| `biggest_wins` | `competition=None, season=None, limit=10` | `list[dict]`: `winner`, `loser`, `score`, `goal_difference` |
| `best_team_record` | `competition=None, season=None, venue=None, metric="win_rate", top=5` (`metric` ∈ `win_rate`/`points`/`goals_for`) | `list[dict]` |
| `derbies` | `season=None, competition=None` | `list[dict]`: `derby`, `teams`, `matches_found` |
| `data_summary` | — | `dict` (delegates to `loader.get_data_summary`) |

### `loader`

`DATA_DIR` (= `<repo root>/data/kaggle`), `load_matches() -> pd.DataFrame` (`lru_cache`
size 1), `load_players() -> pd.DataFrame` (`lru_cache` size 1), `get_data_summary() -> dict`,
`clear_cache() -> None`.

### `normalize`

`normalize_team(name) -> str` (display name; accents kept, state suffix and parentheticals
stripped), `team_key(name) -> str` (accent-folded lowercase match key),
`derby_name(team_a, team_b) -> str | None`.

## Data schemas

No database. Two in-memory pandas DataFrames.

**Match frame** (`load_matches()`) — columns: `date` (ISO `YYYY-MM-DD` or null),
`competition`, `season`, `home_team`, `away_team`, `home_goal`, `away_goal`, `round`,
`stage`, `venue`, `source`, `home_key`, `away_key`, `home_corner`, `away_corner`,
`home_shots`, `away_shots`, `home_attack`, `away_attack`, `total_corners`.
Deduplicated on `(home_key, away_key, date, home_goal, away_goal)`; rows with a null date
are exempt from dedup. Collisions resolved by a `_richness` score (count of non-null
`home_corner`/`home_shots`/`home_attack`), so the stats-carrying BR-Football row wins.

**Player frame** (`load_players()`) — FIFA columns `ID`, `Name`, `Age`, `Nationality`,
`Overall`, `Potential`, `Club`, `Position`, `Jersey Number`, `Height`, `Weight`, `Value`,
`Wage`, plus 34 skill columns, plus derived `club_key` and `name_key`.

**Canonical competitions** (`models.COMPETITIONS`): Brasileirão Série A / B / C, Copa do
Brasil, Copa Libertadores.

**Dataclasses:** `Match` (17 fields), `TeamRecord` (+ computed `goal_difference`, `points`,
`win_rate`), `Standing` (10 fields), `Player` (14 fields). `Player` is declared in
`models.py` but is not constructed anywhere — `queries._player_row_to_dict` builds the
player dict directly from the DataFrame row.
