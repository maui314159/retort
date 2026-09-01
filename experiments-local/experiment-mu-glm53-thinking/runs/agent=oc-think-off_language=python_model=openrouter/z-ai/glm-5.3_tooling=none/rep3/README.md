# Brazilian Soccer MCP with spec and basic data sets

## Running the MCP server

```bash
pip install -r requirements.txt
python server.py        # stdio transport
```

Tools exposed: `find_matches`, `head_to_head`, `last_match_between`,
`team_stats`, `compare_teams`, `standings`, `champion`, `search_players`,
`top_players_at_club`, `team_competitions`, `competition_stats`,
`biggest_wins`, `best_team_record`, `dataset_overview`.

## Tests

```bash
python -m pytest tests/ -q
```

## Specification
brazilian-soccer-mcp-guide.md

## Data Sources
Kaggle data can't be downloaded without an account so these (freely available with attribution) data sets have been downloaded for use here:

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
