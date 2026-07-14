# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes a knowledge-graph-style
query interface over Brazilian soccer data — Brasileirão Serie A/B/C, Copa do
Brasil, Copa Libertadores, the historical Brasileirão (2003–2019) and a FIFA
player database. Connect it to any MCP-compatible LLM client (Claude Desktop,
etc.) to answer natural-language questions about players, teams, matches and
competitions.

## Specification

See [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) and
[`TASK.md`](TASK.md) for the full requirements.

## Data Sources

Kaggle datasets (freely available with attribution) are bundled in
`data/kaggle/`:

| File | Records | License |
|------|---------|---------|
| `Brasileirao_Matches.csv` | 4,180 matches | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | 1,337 matches | CC BY 4.0 |
| `Libertadores_Matches.csv` | 1,255 matches | CC BY 4.0 |
| `BR-Football-Dataset.csv` | 10,296 matches (with corners/shots/attacks) | CC0 |
| `novo_campeonato_brasileiro.csv` | 6,886 matches (2003–2019) | CC BY 4.0 |
| `fifa_data.csv` | 18,207 players | Apache 2.0 |

Sources:
- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data

## What was implemented

- **`normalize.py`** — Canonicalizes team names (state suffixes, accents, full
  legal names), competition labels and the three date formats present in the
  data (ISO, ISO+time, Brazilian DD/MM/YYYY).
- **`data_loader.py`** — Loads all six CSVs once into a unified `Match` /
  `Player` model with normalized team keys, states and scores.
- **`queries.py`** — The query engine. Handles team-name variants
  (`Flamengo` == `Flamengo-RJ`), disambiguates same-base rivals
  (`Atlético-MG` vs `Atlético-PR`), and **deduplicates overlapping fixtures**
  across the `Brasileirao_Matches` and `BR-Football-Dataset` files (which
  describe the same Serie A matches, sometimes with ±1-day date drift) so
  standings, win rates and goal averages are not double-counted.
- **`server.py`** — A FastMCP server exposing 14 tools and 2 resources over
  stdio. Each tool returns a compact text answer plus an embedded JSON payload.
- **`features/`** + **`tests/test_bdd.py`** — BDD (Gherkin) test scenarios
  covering match, team, player, competition and statistical queries plus the
  MCP tool surface.

### MCP tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find fixtures by team, opponent, competition, season, venue, date range |
| `head_to_head` | Compare two teams head-to-head (wins/draws/goals) |
| `team_stats` | Win/loss/draw record and goals for a team |
| `team_competitions` | List competitions and seasons a team appears in |
| `search_players` | Search FIFA players by name, nationality, club, position, rating |
| `top_players` | Highest-rated players (optionally filtered) |
| `brazilian_players_by_club` | Brazilian players grouped by club |
| `competition_standings` | League table calculated from match results |
| `competition_seasons` | Seasons available for a competition |
| `biggest_wins` | Largest victory margins |
| `average_goals` | Average goals/match + home/away/draw rates |
| `best_record` | Rank teams by home or away win rate |
| `derbies` | Traditional derby matches (Fla-Flu, Gre-Nal, Majestoso, …) |
| `catalog` | Data catalog (competitions, seasons, team/player counts) |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run the MCP server

```bash
python server.py
```

Register it with an MCP client (e.g. Claude Desktop) as a stdio server pointing
at `python /path/to/server.py`.

## Run the tests

```bash
pytest -q
```

27 BDD scenarios across 5 feature files verify match queries, team queries
(including team-name-variant resolution and head-to-head invariants), player
queries, competition standings (the 2019 Brasileirão champion resolves to
Flamengo with 90 pts / 28W-6D-4L, matching the spec example), statistical
analysis, and the MCP tool surface.

## Performance

Data loads in <1s; simple lookups and aggregate queries both answer in <10ms
(the spec requires <2s / <5s respectively).

## Data-quality handling

- **Team name variants** collapse via de-accenting, state-suffix stripping and
  a canonical club resolver (`queries.CLUB_CANON`) for ambiguous/multi-word
  names.
- **Cross-file deduplication** merges the two Brasileirão sources on
  competition + date (±1 day tolerance) + canonical team identity, preferring
  the record that carries a score.
- **Missing scores** (100 rows across the match files) are carried through
  match listings but excluded from win/loss/goal aggregates.
- **UTF-8** is used throughout for Portuguese accents (São Paulo, Grêmio, Avaí).
