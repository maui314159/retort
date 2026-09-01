# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes a knowledge graph of
Brazilian soccer (2003-2023): matches, teams, players, competitions,
standings, derbies and statistics, built from six freely-licensed Kaggle
datasets. Connect it to any MCP host/LLM and ask natural-language questions
like *"Who won the 2019 Brasileirão?"* or *"Show me the last Fla-Flu"*.

## Quick start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# run the MCP server (stdio transport, the standard for MCP hosts)
python server.py
```

Register it with an MCP host (Claude Desktop, opencode, ...) as a stdio
command, e.g.:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "venv/bin/python",
      "args": ["server.py"]
    }
  }
}
```

## Tools

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?", "Find all Copa do Brasil finals" (filters: team, opponent, competition, season, stage, date range) |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `team_stats` | "What is Corinthians' home record in 2022?" (per season/competition/venue) |
| `team_profile` | "What competitions has Palmeiras played in?", FIFA squad summary |
| `league_standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?", "Which team has the best away record?" (home/away tables too) |
| `finals` | "Find all Copa do Brasil finals", "Who won the 2020 Libertadores?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `competition_info` | "What's the average goals per match in the Brasileirão?", season comparisons |
| `search_players` | "Who is Neymar?", "Show me all forwards from Santos" (FIFA database) |
| `players_by_club` | "Brazilian players at Brazilian clubs" (counts + avg ratings) |
| `derby_matches` | "Show me all derbies in 2023", "When was the last Gre-Nal?" |

Team names are matched leniently across spellings (`Palmeiras-SP`,
`Palmeiras - SP`, `PALMEIRAS` and `Atletico Mineiro` all resolve correctly);
ambiguous names (bare `Atletico`) return a disambiguation list.

## Architecture

```
server.py                  MCP server (stdio) - thin wrapper around the service
brazilian_soccer/
  normalize.py             team-name folding, aliases, TeamRegistry, date parsing
  models.py                Match / Player / TeamRecord dataclasses
  competitions.py          competition ids and query aliases
  derbies.py               registry of famous clássicos
  loader.py                loads + merges the six CSVs into one graph
  service.py               all query capabilities (used by tools and tests)
tests/                     BDD (Given/When/Then) pytest suites
data/kaggle/               the provided datasets
```

The whole graph loads in ~1.5 s and answers from memory: simple lookups run
in single-digit milliseconds, the heaviest aggregate in ~0.3 s (spec budget:
<2 s / <5 s).

### Cross-file merging

The datasets overlap, so the loader deduplicates and enriches:

- **Brasileirão Serie A** merges the 2012-2022 file, the 2003-2019
  historical file (identical on the overlap - duplicates dropped) and the
  extended-stats file (attaches corners/shots/attacks, fills the unplayed
  2022 late rounds, and is the only source for 2023).
- **Copa do Brasil** merges the round-labelled 2012-2021 file with the
  extended file's 2014-2023 results (fills unplayed ties, adds 2022-2023).
- **Série B / Série C** come from the extended file (join keyed with the
  date because group stages can pair the same teams twice per season).
- **COVID calendar**: league matches played in Jan/Feb belong to the
  previous season (the 2020 Serie A/B/C ran into early 2021); the 2020
  Copa do Brasil final rounds ran into March/April 2021.
- Finals are identified per season (highest played cup round, or the last
  two recorded matches for 2021-2023), and two-leg winners are computed
  with aggregate scores (and the away-goals rule where it applied).

### Data quality notes

- Team-name variants are unified via folding + curated aliases, including
  fixes for source errors: Vitória (BA) is mislabelled `ES` in two files,
  the historical file writes bare `Vasco` with a separate state column,
  and `CA Bragantino` became Red Bull Bragantino (the small Bragantino-PA
  stays separate).
- One junk row in the extended file (`GE Bage x Monsoon FC`) is skipped.
- The FIFA dataset is from the FIFA 19 era: Flamengo, Palmeiras,
  Corinthians, São Paulo and Vasco are absent due to licensing; the server
  explains this when queried (18,207 players, 827 Brazilians).
- The 2023 Serie A snapshot in the extended file differs from the official
  final table; all computed standings reflect the provided data (2019,
  2020 and 2022 tables match the official records exactly).
- Results the datasets cannot express (e.g. the scoreless 2022
  Libertadores final row) are reported honestly, with small clearly-marked
  notes where a fact is known but not recorded.

## Testing

BDD-style pytest suites (Given/When/Then scenarios), including a live
end-to-end test that launches the MCP server over stdio and calls its
tools:

```bash
venv/bin/python -m pytest
```

120 tests cover match/team/player/competition/statistics queries, the 20+
sample questions from the specification, normalization edge cases,
cross-file deduplication invariants, and the MCP protocol integration.

## Data Sources

Kaggle data can't be downloaded without an account so these (freely
available with attribution) data sets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/Brasileirao_Matches.csv
- data/kaggle/Brazilian_Cup_Matches.csv
- data/kaggle/Libertadores_Matches.csv

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- data/kaggle/BR-Football-Dataset.csv

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv

## License

The code in this repository is for demo/non-commercial use. The bundled
datasets carry their own licenses (CC BY 4.0, CC0, Apache 2.0) listed
above.
