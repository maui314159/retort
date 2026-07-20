# Flow

```mermaid
sequenceDiagram
    participant Client as MCP client (stdio)
    participant Host as Program.cs host
    participant DS as DataService
    participant MT as MatchTools

    Host->>DS: LoadAsync() at startup
    DS->>DS: CsvHelper reads 6 CSVs, normalizes team names
    DS-->>Host: Matches (~23k), Players (~18k) in memory
    Client->>MT: tools/call SearchMatches(team, season, ...)
    MT->>DS: Matches (LINQ filter)
    MT->>MT: TeamNameNormalizer.Matches() per row
    MT-->>Client: formatted text (max `limit` rows, newest first)
```

At startup the host eagerly loads all six CSVs into two in-memory lists, normalizing every team name once at load time. Each MCP tool call is a synchronous LINQ scan over `DataService.Matches`/`Players` with `TeamNameNormalizer.Matches()` (alias table + suffix stripping + bidirectional contains) applied per row, then a `StringBuilder`-formatted text response capped by a clamped `limit`. Notable: full linear scans per query (no indexes — fine at this scale), no dedup across the overlapping match datasets, output is prose text rather than structured JSON, and date filters parse with culture-sensitive `DateTime.TryParse`.
