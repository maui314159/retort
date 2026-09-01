# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server exposing a queryable knowledge model
over Brazilian soccer data: Brasileirão Séries A/B/C, Copa do Brasil, Copa
Libertadores matches (2003-2023) and a FIFA player snapshot (18,207 players).
Implemented per `TASK.md` / `brazilian-soccer-mcp-guide.md`.

## Quick start

```bash
# dependencies (a virtualenv with Python 3.12 was used during development)
pip install -r requirements.txt

# run the tests (BDD given/when/then suite over the real datasets)
python -m pytest tests/

# start the MCP server (stdio transport)
python server.py
```

Connect it to any MCP client (Claude Desktop, Claude Code, opencode, ...):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

## What was implemented

| Layer | File | Responsibility |
|-------|------|----------------|
| Domain model | `brazilian_soccer_mcp/models.py` | Unified `Match` / `Player` / `TeamRecord` entities across all six CSVs |
| Name normalization | `brazilian_soccer_mcp/normalizer.py` | Canonical club identity registry handling state suffixes, accents, full names, foreign markers, and same-base club collisions |
| Ingestion | `brazilian_soccer_mcp/loaders.py` | Loads all 6 datasets, multi-format date parsing, cross-source deduplication, per-season source authority |
| Query engine | `brazilian_soccer_mcp/service.py` | Match search, head-to-head, standings, champions, relegation, player search, aggregate statistics |
| Rendering | `brazilian_soccer_mcp/formatting.py` | The "Example answer format" output style from the spec |
| MCP surface | `brazilian_soccer_mcp/server.py` + `server.py` | 20 tools over stdio (`mcp` SDK v2.x) |
| Tests | `tests/` | 198 BDD GWT scenarios (pytest + in-memory MCP client) |

### The 20 MCP tools

**Matches:** `search_matches` (team/opponent/competition/season/date-range/stage),
`head_to_head`, `finals`
**Teams:** `team_record` (season/competition/home/away), `team_overview` (cross-file)
**Competitions:** `standings`, `champion`, `relegated`, `list_competitions`, `list_seasons`
**Statistics:** `competition_stats` (avg goals, home/draw/away rates),
`biggest_wins`, `best_records`, `derbies`, `compare_seasons`
**Players:** `search_players`, `player_profile`, `club_squad`,
`top_brazilian_players`, `brazilians_at_brazilian_clubs`

### Data-quality decisions worth knowing

- **Team identity, not string cleanup.** The datasets contain genuinely
  different clubs sharing a base name (Atlético-MG/PR/GO, Flamengo-RJ vs
  Flamengo-PI, Botafogo-RJ/SP, América-MG/RN). The registry keeps the state
  suffix exactly when a base name is ambiguous, unifies spellings otherwise
  ("Palmeiras-SP" ≡ "Palmeiras", "Atlético Mineiro" ≡ "Atlético-MG"), and
  never merges foreign clubs with Brazilian ones ("Barcelona-EQU" ≠
  "FC Barcelona").
- **Cross-source deduplication.** Série A 2012-2019 appears in three files
  and Copa do Brasil 2014-2021 in two; dedup keys on fixture identity
  (pairing + score), because sources often record different dates for the
  same fixture. Aggregations pinned to one competition+season use the single
  most authoritative source so nothing is double-counted.
- **Cup finals.** Libertadores finals come from the recorded stage; Copa do
  Brasil finals from the highest cup round, with a last-played-dates
  fallback for seasons whose round data is missing or truncated (2021-2023).
  Penalty-shootout decisions are not in the data and are reported honestly.
- **Coverage gaps are reported, not hidden.** The FIFA snapshot (2019 era)
  lacks Flamengo, Palmeiras, Corinthians, São Paulo and Vasco squads; some
  late-2022 league fixtures are recorded without scores. Tools say so
  explicitly, and partial standings carry a note.
- **Determinism.** Bare ambiguous names resolve by curated default, then by
  frequency (e.g. bare "Fluminense" → Fluminense-RJ, never the Piauí club).

### Verified example answers (from the shipped tests)

- 2019 Brasileirão champion: **Flamengo, 90 pts (28W 6D 4L)** — matches the
  spec's example exactly; runner-up Santos via the Brazilian wins tie-break.
- 2019 Copa Libertadores final: **Flamengo 2-1 River Plate**.
- 2023 Copa do Brasil final: **São Paulo 2-1 Flamengo on aggregate**.
- Fla-Flu head-to-head in the dataset: **Flamengo 18 wins, Fluminense 15,
  13 draws**.
- Biggest win in the data: **São Paulo 9-1 4 de Julho (Copa do Brasil)**.
- Brasileirão all-time: **2.57 goals/match, 49.7% home wins**.
- 2020 relegated: **Botafogo, Coritiba, Goiás, Vasco da Gama**.

## Testing

BDD given/when/then pytest suites in `tests/`:

- `test_normalizer.py` — every documented naming pattern
- `test_loaders.py` — file coverage, row counts, date formats, dedup
- `test_match_queries.py`, `test_team_queries.py`,
  `test_player_queries.py`, `test_competition_queries.py`,
  `test_statistics.py` — the five capability families of the spec
- `test_server.py` — end-to-end MCP tool calls over an in-memory session
- `test_sample_questions.py` — the spec's sample-question tables as
  executable scenarios (30 questions, satisfying the "at least 20" criterion)

Performance assertions cover the spec budget: simple lookups run in
~1 ms after a one-time ~0.8 s load (limit: 2 s), aggregate queries in
~2-3 ms (limit: 5 s).

## Data sources (unchanged, see licences in TASK.md)

Kaggle datasets redistributed in `data/kaggle/` (CC BY 4.0 / CC0 / Apache 2.0):

- Brasileirão, Copa do Brasil, Libertadores matches (ricardomattos05)
- BR-Football extended statistics (cuecacuela, CC0)
- Campeonato Brasileiro 2003-2019 (macedojleo)
- FIFA players (youssefelbadry10, Apache 2.0)
