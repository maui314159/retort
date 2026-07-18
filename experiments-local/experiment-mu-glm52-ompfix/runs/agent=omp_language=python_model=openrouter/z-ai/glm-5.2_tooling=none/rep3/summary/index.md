# Summary: agent=omp · language=python · model=openrouter/z-ai/glm-5.2 · tooling=none · rep 3

- **Shape:** FastMCP (stdio/SSE) server over a pandas in-memory store built from six Kaggle CSVs — a clean two-layer split (`soccer_data.py` = data/query, `mcp_server.py` = thin tool wrappers).
- **Structure:** 2 source modules (1,121 LOC) + 1 test file (443 LOC, 25 test functions → 36 tests, 0 skipped).
- **Interfaces:** 0 HTTP routes / 1 CLI entrypoint (`--transport`, `--port`) / 15 MCP tools / ~20 exported store methods.
- **Notable:** The team-name normalization is unusually careful for this task — rather than naively stripping the `-SP`/`-MG` state suffix (which would silently merge Atlético-MG with Atlético-GO), it builds an explicit `CANONICAL_ALIASES` registry of ~45 clubs and keeps the state code in the key only where it disambiguates. There is even a test asserting the two Atléticos don't collide (`test_distinct_atletico_not_merged`). The irony is that the one confirmed defect in this run is a normalization miss the registry was built to prevent: the derby table hardcodes the bare key `"atletico"`, which the registry does not resolve, so Clássico Mineiro returns 0 matches instead of 69.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
