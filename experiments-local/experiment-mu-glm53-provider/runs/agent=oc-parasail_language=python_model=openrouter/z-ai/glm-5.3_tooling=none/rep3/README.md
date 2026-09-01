# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that turns the
six included Kaggle CSV datasets into a queryable knowledge base of Brazilian
soccer: matches, teams, players, competitions and statistics. Connect it to any
MCP-capable LLM client and ask questions in natural language — *"Who won the
2019 Brasileirão?"*, *"What's Corinthians' home record in 2022?"*, *"Show me
every Fla-Flu in the dataset"*.

Implemented per the specification in [`TASK.md`](TASK.md) / [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## Quick start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python server.py            # run the MCP server over stdio
python server.py --transport streamable-http --port 8000   # or over HTTP

python -m pytest            # run the BDD test suite (64 tests)
```

The server loads and normalizes all datasets once at startup (~1.5 s) and
answers every query from memory, comfortably inside the spec's performance
budget (simple lookups < 2 s, aggregates < 5 s).

Connecting from an MCP client (e.g. Claude Desktop):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

## Architecture

```
server.py                     MCP server: 18 tools + dataset resource
brazilian_soccer/
├── normalize.py   Team-name folding: accents, state suffixes, spelling drift,
│                  full legal names, country qualifiers, namesake disambiguation
├── loader.py      CSV parsing, season bucketing, per-season source selection,
│                  dedup, cross-file enrichment, indexes
├── models.py      Match / Player / TeamRecord / StandingRow dataclasses
├── analysis.py    Query functions: search, h2h, standings, stats, derbies...
└── formatting.py  Renders answers in the format of the spec's examples
tests/             Gherkin features + step definitions + unit + e2e tests
```

Data is modeled as a small knowledge graph: **teams**, **players**,
**competitions** and **matches** are entities, and the tools expose the
relations between them (team↔team head-to-head, player→club membership,
team→competition participation, match→competition/season).

## MCP tools

| Category | Tools |
|---|---|
| Matches | `search_matches` (team / opponent / competition / season / date range), `head_to_head`, `last_match_between` |
| Teams | `team_stats` (home/away splits), `team_profile`, `team_competitions`, `search_teams` |
| Players | `search_players` (name / nationality / club / position / rating), `player_details` |
| Competitions | `standings` (computed tables), `champion`, `competition_finals`, `list_competitions` |
| Statistics | `biggest_wins`, `competition_stats` (avg goals, home advantage), `best_records`, `derbies`, `compare_seasons` |

Plus the `brazilian-soccer://datasets` resource describing the loaded files.

## Data unification decisions

The six files overlap heavily, so the loader merges them into one model:

* **One source per competition-season.** The 2012–2019 Brasileirão appears in
  three files; Série A/B rows also exist in BR-Football-Dataset. For each
  season the loader picks the source with the most *scored* matches,
  preferring the dedicated competition file whenever it covers ≥ 80 % of the
  best source. The result: Brasileirão 2003–2011 from
  `novo_campeonato_brasileiro.csv`, 2012–2021 from `Brasileirao_Matches.csv`,
  2022–2023 from `BR-Football-Dataset.csv` (the only source with complete
  2022 scores).
* **COVID season re-bucketing.** BR-Football rows are grouped by calendar
  year, but the 2020 Série A/B/C seasons finished in Jan–Feb 2021. League
  rows dated Jan–Mar are assigned to the previous season, so the 2021
  Série A has exactly 380 matches instead of 491.
* **Unplayable rows skipped.** Abandoned/postponed fixtures without scores
  (e.g. the 2015 Boca–River tie, 81 unrecorded late-2022 Brasileirão
  rounds) are dropped and counted in the load report.
* **Cross-file enrichment.** Matches keep corners/shots/attacks and
  half-time results (BR-Football) and stadium names (historical file)
  wherever the same fixture joins on date + teams.
* **Standings are computed from results**, 3 points per win, with a
  provisional-table note when a season's data is incomplete (e.g. 2023 has
  377 of 380 matches).
* **Cup finals are detected per season**: the Libertadores carries an
  explicit `final` stage; the Copa do Brasil file numbers rounds
  inconsistently between seasons, so the final is the highest round played
  over exactly two legs; BR-Football cup seasons (no round data) use the
  last two-legged pairing of the season. Two-legged finals that finish
  level on aggregate are reported as decided on penalties (shootouts are
  not in the data).

## Team-name normalization

The same club appears as `Palmeiras-SP`, `Palmeiras - SP`, `Palmeiras`,
`Sport Club Corinthians Paulista`, `Athletico Paranaense`, `Atletico-PR`,
`Athletico`, `América FC (Minas Gerais)`, `Nacional (URU)`, ... —
1,150 distinct raw names across the files. Every name is folded to a
canonical key by:

1. unicode folding (accents, case, punctuation) — `São Paulo` ≡ `Sao Paulo`;
2. stripping parenthetical qualifiers and trailing state/country codes —
   `Palmeiras-SP` → `palmeiras`, `America MG` → `america`;
3. a curated alias table for legal names (`Sport Club do Recife` → Sport
   Recife), spelling drift (`Athletico`/`Atlético` Paranaense) and
   country-qualified foreign clubs (`Barcelona-EQU` ≠ FC Barcelona);
4. namesake protection: a state suffix that disagrees with a canonical
   club's home state creates a *separate* club — `Flamengo - PI`,
   `Botafogo - PB` and `América - RN` are not Flamengo, Botafogo or
   América Mineiro.

Queries through the registry are forgiving: `palmeirass`,
`corinthians` or `atletico-mg` all resolve, with `search_teams` available
to explore matches.

## Sample questions (all answerable)

| # | Question | Tool call |
|---|---|---|
| 1 | Show me all Flamengo vs Fluminense matches | `search_matches team=Flamengo opponent=Fluminense` |
| 2 | What matches did Palmeiras play in 2023? | `search_matches team=Palmeiras season=2023` |
| 3 | Find all Copa do Brasil finals | `competition_finals competition="Copa do Brasil"` |
| 4 | When did Flamengo last play Corinthians? | `last_match_between team_a=Flamengo team_b=Corinthians` |
| 5 | What matches happened in June 2023? | `search_matches date_from=2023-06-01 date_to=2023-06-30` |
| 6 | What is Corinthians' home record in 2022? | `team_stats team=Corinthians season=2022` |
| 7 | Which team scored the most goals in Serie A 2023? | `standings competition=Brasileirão season=2023` (GF column) |
| 8 | Compare Palmeiras and Santos head-to-head | `head_to_head team_a=Palmeiras team_b=Santos` |
| 9 | Which players play for Fluminense? | `search_players club=Fluminense` |
| 10 | Find all Brazilian players | `search_players nationality=Brazil` |
| 11 | Who are the highest-rated Brazilian players? | `search_players nationality=Brazil` (sorted by rating) |
| 12 | Show me all forwards from Santos | `search_players club=Santos position=forward` |
| 13 | Who is Neymar? | `player_details name=Neymar` |
| 14 | Who won the 2019 Brasileirão? | `champion competition=Brasileirão season=2019` |
| 15 | Who won the 2019 Copa do Brasil? | `champion competition="Copa do Brasil" season=2019` |
| 16 | Show the Libertadores finals | `competition_finals competition=Libertadores` |
| 17 | Which teams were relegated in 2020? | `standings competition=Brasileirão season=2020` (bottom four) |
| 18 | Show me the 2019 league table | `standings competition=Brasileirão season=2019` |
| 19 | What competitions has Palmeiras played in? | `team_competitions team=Palmeiras` |
| 20 | What's the average goals per match in the Brasileirão? | `competition_stats competition=Brasileirão` |
| 21 | Which team has the best away record (2023)? | `best_records venue=away competition=Brasileirão season=2023` |
| 22 | Show me the biggest wins in the dataset | `biggest_wins` |
| 23 | Show me all derbies in 2023 | `derbies season=2023` |
| 24 | Compare the 2018 and 2019 seasons | `compare_seasons season_a=2018 season_b=2019` |
| 25 | Is 'palmeiras-sp' the same as 'Palmeiras'? | `search_teams query=palmeiras-sp` |

## Testing

BDD (Gherkin) scenarios in `tests/features/` mirror the spec's testing
approach, wired to step definitions with `pytest-bdd`; plus direct unit
tests for normalization/parsing and a true end-to-end test that launches
`server.py` as a subprocess and drives it through an MCP `ClientSession`
over stdio.

```bash
python -m pytest                  # everything
python -m pytest tests/test_statistics.py -v   # one feature
```

Feature files: `match_queries`, `team_queries`, `player_queries`,
`competition_queries`, `statistics`, `normalization`, `mcp_server`,
`performance` — 64 tests total.

## Data sources & licenses

| File | Contents | License |
|---|---|---|
| `data/kaggle/Brasileirao_Matches.csv` | Brasileirão 2012–2022 | CC BY 4.0 |
| `data/kaggle/Brazilian_Cup_Matches.csv` | Copa do Brasil 2012–2021 | CC BY 4.0 |
| `data/kaggle/Libertadores_Matches.csv` | Libertadores 2013–2022 | CC BY 4.0 |
| `data/kaggle/BR-Football-Dataset.csv` | Série A/B/C + Copa do Brasil 2014–2023, with corners/shots/attacks | CC0 |
| `data/kaggle/novo_campeonato_brasileiro.csv` | Brasileirão 2003–2019, with stadiums | CC BY 4.0 |
| `data/kaggle/fifa_data.csv` | 18,207 FIFA players | Apache 2.0 |

## Known limitations

* The FIFA file (FIFA 19 era) does not include every Brazilian club —
  Flamengo, Palmeiras, Corinthians, São Paulo and Vasco have no player
  rows; clubs that are covered (Grêmio, Santos, Fluminense, ...) carry
  generated squads. Player queries against missing clubs return a clear
  "no players recorded" answer.
* Top scorers per season cannot be computed — none of the files records
  goal scorers.
* The 2021 Copa do Brasil file is truncated after the round of 16, and the
  Libertadores file is missing the 2021 final entirely; those finals are
  simply absent from the answers.
* Penalty shootouts are not recorded, so finals level on aggregate report
  both finalists with a note.
