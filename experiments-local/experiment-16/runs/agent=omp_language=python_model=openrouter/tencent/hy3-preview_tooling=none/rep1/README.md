# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that provides a knowledge graph interface for Brazilian soccer data. The server enables natural language queries about players, teams, matches, and competitions using the provided datasets.

## Features

- **Match Queries**: Search matches by team, competition, season, or date range
- **Team Statistics**: Get team records, wins/losses, goals, win rates
- **Head-to-Head**: Calculate head-to-head records between two teams
- **Player Queries**: Search FIFA player database by name, nationality, club
- **Competition Standings**: Calculate standings from match results
- **Statistical Analysis**: Average goals, biggest wins, team comparisons

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Running the MCP Server

```bash
python server.py
```

The server uses stdio transport by default. Connect to it using any MCP client.

### Available Tools

1. **search_matches** - Search for matches by team, competition, season, date
2. **get_team_stats** - Get team statistics
3. **head_to_head** - Get head-to-head record between two teams
4. **search_players** - Search FIFA player database
5. **get_competition_standings** - Get competition standings
6. **get_biggest_wins** - Find biggest wins in dataset
7. **compare_teams** - Compare two teams' statistics
8. **get_average_goals** - Calculate average goals per match
9. **get_competitions** - List all available competitions
10. **get_seasons** - List all available seasons

## Data Sources

The server uses the following datasets from the `data/kaggle/` directory:

- `Brasileirao_Matches.csv` - Brasileirão Serie A matches (4,180 matches)
- `Brazilian_Cup_Matches.csv` - Copa do Brasil matches (1,337 matches)
- `Libertadores_Matches.csv` - Copa Libertadores matches (1,255 matches)
- `BR-Football-Dataset.csv` - Extended match statistics (10,296 matches)
- `novo_campeonato_brasileiro.csv` - Historical Brasileirão 2003-2019 (6,886 matches)
- `fifa_data.csv` - FIFA player database (18,207 players)

## Example Queries

Once connected to an MCP client, you can ask:

- "Show me all Flamengo vs Fluminense matches"
- "What is Corinthians' home record in 2022?"
- "Find all Brazilian players in the dataset"
- "Who won the 2019 Brasileirão?"
- "What's the average goals per match in the Brasileirão?"

## Testing

Run the test suite:

```bash
pytest test_server.py -v
```

## License

Data files are licensed under their respective licenses (CC BY 4.0, CC0, Apache 2.0).
