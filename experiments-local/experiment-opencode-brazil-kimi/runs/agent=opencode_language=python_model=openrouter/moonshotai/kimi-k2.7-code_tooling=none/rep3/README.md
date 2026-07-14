# Brazilian Soccer MCP with spec and basic data sets

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

## Implementation

The project implements an MCP (Model Context Protocol) server in Python that
answers questions about the bundled datasets. Code lives in the
`brazilian_soccer_mcp` package:

- `normalize.py` – handles Brazilian date formats, UTF-8 text, score parsing
  and normalises team-name variants (e.g. "Flamengo-RJ" vs "Flamengo").
- `data_loader.py` – loads all six CSVs, normalises records and de-duplicates
  overlapping league fixtures.
- `engine.py` – read-only query engine for matches, teams, players,
  competitions and statistics.
- `server.py` – `mcp.server.fastmcp` stdio server exposing the engine as MCP
  tools.

## Running the server

```bash
python -m brazilian_soccer_mcp
```

Or:

```bash
python main.py
```

## Running the tests

```bash
python -m pytest tests -q
```

A virtual environment is recommended:

```bash
python -m venv venv
venv/bin/pip install -e '.[dev]'
venv/bin/pytest tests -q
```
