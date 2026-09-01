# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that provides a knowledge interface over
Brazilian soccer data: matches, teams, competitions and players. It is designed
to be connected to an LLM client (Claude Desktop, any MCP host) so natural
language questions like *"Who won the 2019 Brasileirão?"* or *"Show me all
Fla-Flu matches"* can be answered from the bundled datasets.

Full specification: [`TASK.md`](TASK.md) (aka `brazilian-soccer-mcp-guide.md`).

## Quick start

```bash
# create/activate the environment (Python 3.12+)
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# run the MCP server over stdio (the MCP default transport)
./venv/bin/python server.py
```

Point your MCP client at the server, e.g. for Claude Desktop:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

## What was implemented

### Data layer (`brazilian_soccer/`)

All six Kaggle datasets under `data/kaggle/` are loaded, normalized and indexed
in memory (~0.6 s, ~17k unique matches, 18k players):

| Dataset | Contents |
|---|---|
| `Brasileirao_Matches.csv` | Série A 2012–2022 |
| `Brazilian_Cup_Matches.csv` | Copa do Brasil 2012–2021 |
| `Libertadores_Matches.csv` | Copa Libertadores (incl. foreign clubs) |
| `BR-Football-Dataset.csv` | Série A/B/C + Copa do Brasil 2014–2023 with corners/attacks/shots |
| `novo_campeonato_brasileiro.csv` | Série A 2003–2019 (PT-BR columns, DD/MM/YYYY dates) |
| `fifa_data.csv` | FIFA 19 player database |

Key data-quality handling:

- **Team-name identity** (`normalize.py`): 625 raw name variants ("Palmeiras-SP",
  "Palmeiras - SP", "Sao Paulo", "São Paulo", "Athletico Paranaense",
  "Nacional (URU)") collapse to ~1000 stable canonical clubs. State suffixes are
  part of identity only where the base name is genuinely ambiguous (Botafogo-RJ
  vs Botafogo-PB vs Botafogo-SP); country codes in Libertadores data always
  denote separate clubs; bare names of famous clubs resolve via a curated
  default ("Vasco" → Vasco da Gama-RJ).
- **Cross-source de-duplication** (`loader.py`): the same real match appears in
  up to three files (e.g. Série A 2014–2019). Rows are matched on canonical keys
  and reduced to one, preferring rows with actual scores and richer sources, so
  statistics never double-count. Série A 2019 computes to exactly 380 matches.
- **Date formats**: ISO, ISO+time and Brazilian DD/MM/YYYY all parsed; the
  COVID-affected 2020 season (played into Feb 2021) is attributed correctly.
- **Cup stages**: finals/semifinals derived from rounds, robust to truncated
  seasons (the 2021 final comes from the extended-stats file).
- **UTF-8**: accented display names ("São Paulo", "Grêmio", "Avaí") preserved
  everywhere; matching is accent/case-insensitive.

### MCP server (`server.py`)

14 tools (all return JSON, all accept fuzzy team/competition names):

| Category | Tools |
|---|---|
| Match queries | `search_matches` (team/opponent/competition/season/stage/date-range), `get_head_to_head` |
| Team queries | `get_team_stats` (record, home/away), `get_team_history`, `list_teams` |
| Competition queries | `get_competitions`, `get_standings` (computed from results, incl. champion + relegation zone), `compare_seasons` |
| Player queries | `search_players`, `get_player`, `search_players_at_club` |
| Statistical analysis | `get_statistics` (avg goals, home/away win rates, biggest wins, best records), `get_derbies` |
| NL fallback | `answer_question` — deterministic router so simple questions work without an LLM |

Resources: `soccer://status`, `soccer://teams`, `soccer://competitions`,
`soccer://derbies`.

The LLM integration pattern: an MCP host connects to this server and maps user
questions onto the structured tools above; `answer_question` is a best-effort
deterministic fallback for direct use.

## Testing

BDD (Gherkin) scenarios plus unit, end-to-end and sample-question suites:

```bash
./venv/bin/python -m pytest tests/ -q          # 112 tests
./venv/bin/python -m pytest tests/ -q --cov    # with coverage
```

- `tests/features/*.feature` + `tests/step_defs/` — BDD scenarios for the five
  required capability areas (match/team/player/competition/statistics) and a
  data-quality feature (name variants, date formats, UTF-8, cross-file links).
- `tests/test_sample_questions.py` — 25 questions from the specification,
  each answered and asserted (including graceful not-found answers).
- `tests/test_mcp_server.py` — end-to-end: spawns the real server process and
  drives it over stdio with the MCP client SDK (tools, errors, resources).
- `tests/test_loader_and_store.py` — data coverage, de-duplication integrity
  (380 matches/season, 38 per team), cross-file player↔team links, and the
  performance budgets (<2 s lookups, <5 s aggregates).
- Known data limitations are tested, not hidden: the FIFA export lacks some
  Brazilian clubs (e.g. no Flamengo/Corinthians squads) and omits Gabriel
  Barbosa; one Libertadores row has no date; ~100 postponed fixtures have no
  score and are excluded from statistics.

## Project layout

```
server.py                      MCP server entry point (stdio)
brazilian_soccer/
  normalize.py                 team identity, aliases, dates, parsing
  models.py                    Match/Player dataclasses
  loader.py                    CSV loading, season/cup-stage derivation, dedupe
  analytics.py                 standings, records, h2h, aggregates (pure functions)
  store.py                     SoccerStore: indexes + query surface
  tools.py                     deterministic NL question router
tests/
  features/                    Gherkin feature files (BDD)
  step_defs/                   pytest-bdd step definitions
  test_*.py                    unit, sample-question and MCP e2e tests
data/kaggle/                   the six source datasets (see licenses below)
```

## Data sources & licenses

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro — CC BY 4.0
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches — CC0
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 — CC BY 4.0
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data — Apache 2.0

Demo/non-commercial use only, per the specification.
