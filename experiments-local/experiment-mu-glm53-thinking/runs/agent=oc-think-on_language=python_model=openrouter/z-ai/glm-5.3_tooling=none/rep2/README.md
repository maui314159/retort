# Brazilian Soccer MCP Server

A Model Context Protocol (MCP) server that answers natural-language questions
about Brazilian soccer — matches, teams, players, competitions and statistics —
over the Kaggle datasets included in this repository. Built to the
specification in `TASK.md` / `brazilian-soccer-mcp-guide.md`.

## Quick start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m brazilian_soccer_mcp        # runs the MCP server over stdio
```

Register it with any MCP client, e.g. for Claude Desktop:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "venv/bin/python",
      "args": ["-m", "brazilian_soccer_mcp"],
      "cwd": "/absolute/path/to/this/repo"
    }
  }
}
```

## What was built

| Component | Purpose |
|-----------|---------|
| `brazilian_soccer_mcp/models.py` | `Match` / `Player` dataclasses |
| `brazilian_soccer_mcp/normalize.py` | Team-name canonicalisation (alias table + state/country-tag rules), date parsing (ISO / ISO+time / Brazilian), competition mapping, derby knowledge base |
| `brazilian_soccer_mcp/loader.py` | Loads all six CSVs, builds a de-duplicated "primary" view per (competition, season), joins extended stats (corners/shots/attacks) across files |
| `brazilian_soccer_mcp/service.py` | Query/analysis engine: match search, head-to-head, records, standings, players, statistics |
| `brazilian_soccer_mcp/server.py` | MCP server exposing 18 tools |
| `tests/` | BDD (Gherkin Given/When/Then) pytest suite, 88 scenarios |

### Data-handling notes

- **Team names** — every spelling ("Palmeiras-SP", "Palmeiras", "Palmeiras - SP",
  "América FC (Minas Gerais)", "Athletico"/"Atletico-PR") resolves to one
  canonical id; ambiguous clubs (Botafogo-RJ vs -PB, América-MG vs -RN) keep
  their state suffix.
- **De-duplication** — the 2012-2019 Série A exists in two files and the
  BR-Football file overlaps everything; the loader picks one authoritative
  source per (competition, season), preferring completeness (e.g. the 2022
  Série A is taken from BR-Football because the dedicated file is missing 81
  scores). Extended corner/shot/attack stats are still joined onto the
  primary matches.
- **Season attribution** — BR-Football has no season column; Brazilian league
  seasons run May-December, so January/February rows are assigned to the
  previous year's season (COVID-delayed 2020 season).
- **Validation** — computed standings reproduce all 20 real Série A champions
  from 2003-2022 (e.g. 2019 Flamengo: 90 pts, 28W-6D-4L) and the real
  relegated teams.

## Tools (18)

`search_matches`, `head_to_head`, `last_meeting`, `find_finals`, `derbies`,
`team_record`, `team_profile`, `list_teams`, `best_records`,
`search_players`, `top_players`, `club_squad`, `brazilian_players_by_club`,
`competition_info`, `standings`, `stats_summary`, `biggest_wins`,
`season_comparison`.

## Sample questions answered (24 of the 20+ required)

| # | Question | Tool |
|---|----------|------|
| 1 | When did Flamengo last play Corinthians? | `last_meeting` |
| 2 | What was the score? | `last_meeting` |
| 3 | Who is Neymar Jr? | `search_players` |
| 4 | Show me all Flamengo vs Fluminense matches | `head_to_head` |
| 5 | What matches did Palmeiras play in 2023? | `search_matches` |
| 6 | Find all Copa do Brasil finals | `find_finals` |
| 7 | Show the Libertadores 2019 final | `find_finals` |
| 8 | What is Corinthians' home record in 2022? | `team_record` |
| 9 | Which team scored the most goals in Série A 2023? | `standings` |
| 10 | Compare Palmeiras and Santos head-to-head | `head_to_head` |
| 11 | Which players play for Grêmio? | `club_squad` |
| 12 | Show me all derbies in 2023 | `derbies` |
| 13 | What competitions has Palmeiras played in? | `team_profile` |
| 14 | Who won the 2019 Brasileirão? | `standings` |
| 15 | Which teams were relegated in 2020? | `standings` |
| 16 | Which team has the best home record? | `best_records` |
| 17 | Which team has the best away record? | `best_records` |
| 18 | Who are the top Brazilian players? | `top_players` |
| 19 | Find all Brazilian players | `search_players` |
| 20 | Show me all forwards from Santos | `search_players` |
| 21 | What's the average goals per match in the Brasileirão? | `stats_summary` |
| 22 | Show me the biggest wins in the dataset | `biggest_wins` |
| 23 | Compare the 2018 and 2019 seasons | `season_comparison` |
| 24 | What data do you have? | `competition_info` |

## Testing

BDD scenarios (Gherkin Given/When/Then structure) via pytest:

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

88 scenarios across match, team, player, competition, statistics, data-loading,
normalisation and MCP-server behaviour — including a full stdio JSON-RPC
round-trip against the running server. Representative queries answer in
1-20 ms (budgets: simple < 2 s, aggregate < 5 s); dataset load ≈ 1 s.

## Data sources

Kaggle data can't be downloaded without an account so these (freely available
with attribution) data sets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/Brasileirao_Matches.csv (Série A 2012-2022)
- data/kaggle/Brazilian_Cup_Matches.csv (Copa do Brasil 2012-2021)
- data/kaggle/Libertadores_Matches.csv (Copa Libertadores 2013-2022)

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- data/kaggle/BR-Football-Dataset.csv (Série A/B/C + Copa do Brasil 2014-2023,
  with corners/shots/attacks)

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv (Série A 2003-2019)

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv (18,207 players)
