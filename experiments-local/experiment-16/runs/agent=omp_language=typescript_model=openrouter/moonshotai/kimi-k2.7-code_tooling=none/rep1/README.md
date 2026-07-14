# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that answers natural-language questions about Brazilian soccer using the included Kaggle datasets.

## Data Sources

The datasets in `data/kaggle/` are loaded at startup:

- `Brasileirao_Matches.csv` – Série A matches (2012–2022)
- `Brazilian_Cup_Matches.csv` – Copa do Brasil matches
- `Libertadores_Matches.csv` – Copa Libertadores matches
- `BR-Football-Dataset.csv` – extended match statistics
- `novo_campeonato_brasileiro.csv` – historical Brasileirão (2003–2019)
- `fifa_data.csv` – FIFA player database

## Available Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team, opponent, competition, season, date range, or round |
| `team_statistics` | Win/loss/draw and goal stats for a team |
| `head_to_head` | Compare two teams across all datasets |
| `competition_standings` | Calculate league standings for a competition/season |
| `biggest_wins` | Biggest victories by goal difference |
| `search_players` | Search FIFA player data by name, nationality, club, or position |
| `average_goals` | Average goals per match for a competition/season |

## Running

```bash
npm install
npm run build
npm start
```

The server communicates over stdio.

## Testing

```bash
npm test
```

Tests are BDD-style Vitest suites covering match, team, player, competition, and statistical queries.

## License

See individual dataset licenses in `README.md` history. Code is MIT.
