# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server that exposes a knowledge-graph
interface over six Brazilian-soccer datasets, so an LLM client can answer
natural-language questions about matches, teams, players and competitions.

The specification implemented is `TASK.md` (mirrored in
`brazilian-soccer-mcp-guide.md`).

## What was built

A self-contained Python package, `brazilian_soccer/`, with no external services:

| Module | Responsibility |
|--------|----------------|
| `normalize.py` | Canonicalize team names, dates and scores across the datasets. |
| `loader.py` | Read the six CSVs into uniform `MatchRecord` / `PlayerRecord` lists and build the graph. |
| `graph.py` | `SoccerGraph`: in-memory knowledge graph + query engine. |
| `server.py` | `FastMCP` server exposing the queries as MCP tools. |

Everything is loaded once into in-memory indexes (teams, players and matches as
nodes; `PLAYED` / `PLAYS_FOR` as edges), keeping simple lookups well under the
spec's 2 s budget and aggregate queries under 5 s (the full graph loads in
~0.8 s).

### Why no Neo4j

The benchmark scaffolding mentions Neo4j, but `TASK.md` only requires a
"knowledge graph interface" and natural-language queries. A Neo4j server is not
available in this environment, and the data volume (≈17 k matches, ≈18 k
players) fits comfortably in process memory. An in-memory graph is therefore
faster, has zero setup, and is fully unit-testable offline. The node/edge model
and query surface are identical to what a Cypher-backed implementation would
expose, so swapping in a graph database later is a `SoccerGraph` reimplementation
behind the same method signatures.

## MCP tools

| Tool | Capability (spec category) |
|------|----------------------------|
| `search_matches` | Match queries: by team / opponent / competition / season / date range / venue. |
| `head_to_head` | Match queries: W/D/L summary + match list between two teams. |
| `team_record` | Team queries: W/D/L and goals, filterable by season, competition and home/away. |
| `search_players` | Player queries: by name, nationality, club, position, minimum rating. |
| `standings` | Competition queries: league table computed from match results. |
| `average_goals` | Statistics: goals/match plus home/away/draw rates. |
| `biggest_wins` | Statistics: largest-margin matches. |
| `best_records` | Statistics: teams ranked by win rate (home/away/all). |
| `answer` | Free-text router for the common question shapes. |

## Running

```bash
pip install -r requirements.txt        # or: pip install -e .
python -m brazilian_soccer.server      # starts the MCP server over stdio
```

Programmatic use:

```python
from brazilian_soccer import load_graph

g = load_graph()
g.standings("Brasileirão", 2019)[0].team        # -> 'Flamengo'
g.head_to_head("Flamengo", "Fluminense")        # Fla-Flu derby summary
g.find_players(nationality="Brazil", limit=10)   # top-rated Brazilians
```

## Data handling

The datasets are messy and overlapping; the loader resolves this:

- **Team-name variations.** Names are reduced to a canonical, state-aware key.
  The state code comes from the name suffix (`Atletico-MG -> atletico|mg`),
  which is reliable across files and keeps genuinely different clubs apart
  (Atlético-MG vs Atlético-PR vs Atlético-GO). The dedicated state *column* is
  deliberately ignored: the historical file mislabels some home rows (e.g.
  Vitória/BA recorded as ES at home), which would split one club in two.
  A bare query ("Flamengo") resolves to the dominant club by match count, so it
  means Flamengo-RJ rather than the minor Flamengo-PI. Accents, long official
  names ("Sport Club Corinthians Paulista") and cross-source spelling variants
  ("Athletico"/"Atlético", "Vasco da Gama"/"Vasco") are folded together.
- **Overlapping sources.** The Brasileirão appears in three files
  (`Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv`, and
  BR-Football's "Serie A"). For each `(competition, season)` the loader keeps
  only the source with the most *scored* matches, then deduplicates remaining
  rows. This avoids double-counting (which otherwise inflated 2019 to 180 pts)
  and uses BR-Football's complete 2022/2023 scores where the dedicated file has
  gaps. Verified: every Brasileirão season 2003-2019 yields exactly 20 teams /
  38 matches, with 2019 reproducing the known final table (Flamengo 90 pts,
  28 W 6 D 4 L).
- **Date and score formats.** ISO, ISO+time, Brazilian `DD/MM/YYYY` and the
  `2003.01.0001` id form are all parsed; scores stored as int, float, `"2"`,
  `"-"` or blank are normalized, with missing scores excluded from statistics
  but kept in match listings.

### Known data limitations (source, not code)

- The FIFA snapshot is a 2019 version: it includes Brazilian clubs such as
  Grêmio, Santos and Cruzeiro (20 players each) but **not** Flamengo or
  Palmeiras, so club searches for those return empty.
- BR-Football's 2023 Serie A has 377/380 rows, so a couple of 2023 fixtures are
  missing from that season's table.

## Tests

BDD scenarios (Gherkin Given/When/Then via `pytest-bdd`) cover each capability
category, alongside unit tests for normalization and the MCP tool layer, and an
integration suite that asserts known real-world results (2019 champion, dedup
correctness, performance budgets) against the full datasets.

```bash
python -m pytest -q          # 60 tests
```

`tests/features/*.feature` hold the scenarios; `tests/test_*.py` hold the step
definitions and unit/integration tests. The behavior scenarios run against a
small synthetic dataset (`tests/conftest.py`) for exact, fast assertions; the
integration tests load `data/kaggle/` and skip automatically if it is absent.

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets are included here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/Brasileirao_Matches.csv`
- `data/kaggle/Brazilian_Cup_Matches.csv`
- `data/kaggle/Libertadores_Matches.csv`

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- `data/kaggle/BR-Football-Dataset.csv`

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/novo_campeonato_brasileiro.csv`

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- `data/kaggle/fifa_data.csv`
