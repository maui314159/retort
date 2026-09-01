# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
turns the bundled Kaggle datasets into a queryable knowledge base for
Brazilian soccer: matches, teams, players, competitions and statistics.

Connect it to any MCP client (Claude Desktop, opencode, ...) and ask
natural-language questions — the client's LLM drives the tools below.

## Quick start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python server.py          # runs the MCP server over stdio
```

Register it with an MCP client, e.g. in `opencode.json`:

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

## What's inside

```
server.py                    MCP server (15 tools, stdio transport)
brazilian_soccer/
  normalize.py               team-name & competition canonicalization
  dates.py                   multi-format date/goal/money parsing
  models.py                  Match / MatchStats / Player records
  data.py                    loads the 6 CSVs, unifies overlapping files
  queries.py                 query layer behind every tool
tests/                       BDD (Given/When/Then) pytest suite, 90 scenarios
```

## Tools

| Tool | Answers questions like |
|------|----------------------|
| `list_competitions` | "What competitions and seasons are in the data?" |
| `resolve_team` | "What are all the spellings of Corinthians in the files?" |
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?", "Find Libertadores finals", date-range and round filters |
| `head_to_head` | "Compare Palmeiras and Santos", "When did Flamengo last play Corinthians?" |
| `get_team_stats` | "What is Corinthians' home record in 2022?", best home/away records |
| `get_club_overview` | cross-file club profile (match record + FIFA squad) |
| `get_standings` | "Who won the 2019 Brasileirão?" (table computed from results) |
| `get_relegation` | "Which teams were relegated in 2020?" |
| `find_finals` | "Find all Copa do Brasil / Libertadores finals" |
| `search_players` | "Top Brazilian players", "forwards from Santos", club/nationality/rating filters |
| `get_competition_stats` | "Average goals per match in the Brasileirão?", home vs away splits |
| `get_biggest_wins` | "Show me the biggest wins in the dataset" |
| `get_derby_matches` | "Show me Fla-Flu / Gre-Nal / all 2023 derbies" |
| `search_match_stats` | corners, shots and attacks per match (2014-2023) |
| `best_home_records` | "Which team has the best home record?" |

Errors are structured: an unresolvable team name returns
`{"error": ..., }` with spelling suggestions, never a crash.

## Data handling

- **Overlapping files**: the same fixture appears in several CSVs with
  different spellings and dates. Every (competition, season) is served from
  one primary source (richest schedule data first); BR-Football records are
  kept as an extended-statistics layer and joined onto primary matches.
  Cross-file aggregates never double count.
- **Team names**: `Palmeiras-SP`, `Palmeiras`, `Sociedade Esportiva
  Palmeiras` and FIFA spellings all canonicalize to one club. Clubs that
  share a name but differ by state (Flamengo-RJ vs Flamengo-PI,
  Atlético-MG vs Atlético-GO) stay distinct. Foreign clubs keep their
  Libertadores country tags (`Barcelona-EQU` != FC Barcelona).
- **Dates / encodings**: ISO, ISO+time and Brazilian `DD/MM/YYYY` formats
  are parsed; everything is read as UTF-8.
- **Data gaps are disclosed, not hidden**: e.g. the 2022 Brasileirão has
  listed fixtures without recorded scores and the 2023 season is missing
  3 fixtures — those responses carry a `data_note`.

## Testing

BDD-style pytest scenarios (Given/When/Then), including end-to-end tests
that drive the server over the real stdio MCP transport:

```bash
venv/bin/python -m pytest tests/ -q
```

90 scenarios covering match queries, team queries, player queries,
competition queries, statistical analysis, name/date normalization, the
MCP protocol surface and the spec's performance targets (lookups < 2s,
aggregates < 5s).

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
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv

See `TASK.md` / `brazilian-soccer-mcp-guide.md` for the full specification.
