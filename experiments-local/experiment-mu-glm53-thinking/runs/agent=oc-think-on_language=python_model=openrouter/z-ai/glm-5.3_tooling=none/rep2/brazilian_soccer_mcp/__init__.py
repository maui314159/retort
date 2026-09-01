"""Brazilian Soccer MCP Server.

A Model Context Protocol (MCP) server exposing a queryable knowledge base of
Brazilian soccer data built from the Kaggle datasets shipped in ``data/kaggle``:

- Brasileirao_Matches.csv (Serie A 2012-2022)
- novo_campeonato_brasileiro.csv (Serie A 2003-2019)
- Brazilian_Cup_Matches.csv (Copa do Brasil 2012-2021)
- Libertadores_Matches.csv (Copa Libertadores 2013-2022)
- BR-Football-Dataset.csv (Serie A/B/C + Copa do Brasil 2014-2023, extended stats)
- fifa_data.csv (18,207 players)

Run with::

    python -m brazilian_soccer_mcp
"""

__version__ = "1.0.0"

from .loader import SoccerData
from .service import SoccerQueryService

__all__ = ["SoccerData", "SoccerQueryService", "__version__"]
