"""
 brazilian_soccer_mcp / server.py
 ================================

 Why
 ---
 TASK.md asks for an MCP (Model Context Protocol) server that an LLM
 connects to for natural-language questions about Brazilian soccer.  The
 MCP SDK is not a dependency of this environment, so this module
 implements the MCP stdio transport directly on the Python standard
 library: newline-delimited JSON-RPC 2.0 over stdin/stdout, exactly as
 the protocol specifies (https://modelcontextprotocol.io).  No third-
     party packages are required, and the message handling is a plain
 class so tests can drive it without spawning a process.

 What
 ---
 * :class:`MCPServer`       - protocol state machine.  ``handle(msg)``
                              maps one decoded JSON-RPC message to its
                              response (or ``None`` for notifications).
                              Methods: initialize, ping, tools/list,
                              tools/call, resources/list, resources/read.
                              Unknown request methods -> -32601; requests
                              before initialize -> -32002; unknown tools
                              -> -32602 (ToolError).
 * :func:`serve`           - the stdio loop: read a line, dispatch,
                              write the response line, flush.  Never
                              writes anything but protocol JSON to stdout.
 * :func:`main`            - CLI entry point (``python -m
                              brazilian_soccer_mcp [--stdio] [--version]``).

 Resources exposed (MCP resources/list):
   brazilian-soccer://overview        - datasets, schema, normalisation notes
   brazilian-soccer://competitions    - competitions, seasons, match counts
   brazilian-soccer://teams           - club directory
   brazilian-soccer://dataset/<file>  - one resource per source CSV
                                        (columns, rows, licence, source URL)

 Test: ``tests/test_server.py`` (unit + end-to-end subprocess over pipes).
=========================================================================
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import BinaryIO, TextIO

from . import tools
from .loader import COMPETITIONS, DATA_FILES, Dataset, load_dataset

__all__ = ["MCPServer", "main", "serve"]

SERVER_NAME = "brazilian-soccer-mcp"
SERVER_VERSION = "1.0.0"

#: Protocol versions this implementation speaks (echo the client's when known).
SUPPORTED_PROTOCOL_VERSIONS = ["2024-11-05", "2025-03-26", "2025-06-18"]
DEFAULT_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]

_JSONRPC_VERSION = "2.0"

# JSON-RPC / MCP error codes.
_PARSE_ERROR = -32700
_INVALID_REQUEST = -32600
_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602
_INTERNAL_ERROR = -32603
_SERVER_NOT_INITIALIZED = -32002

INSTRUCTIONS = (
    "Brazilian soccer knowledge server. Ask about matches (Brasileirão "
    "Série A 2003-2023, Série B/C, Copa do Brasil, Copa Libertadores), "
    "teams, standings, head-to-head records, derbies, aggregate statistics "
    "and FIFA player data. Team names may be written in any spelling the "
    "datasets use ('Palmeiras-SP', 'Palmeiras', 'Sport Club Corinthians "
    "Paulista'). Start with list_competitions to see seasons covered."
)

_DATASET_META = {
    "Brasileirao_Matches.csv": {
        "description": "Brasileirão Série A fixtures 2012-2022 (round, state suffixes)",
        "source": "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro",
        "license": "CC BY 4.0",
        "columns": [
            "datetime",
            "home_team",
            "home_team_state",
            "away_team",
            "away_team_state",
            "home_goal",
            "away_goal",
            "season",
            "round",
        ],
    },
    "Brazilian_Cup_Matches.csv": {
        "description": "Copa do Brasil fixtures 2012-2021 (numeric rounds 1-8)",
        "source": "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro",
        "license": "CC BY 4.0",
        "columns": [
            "round",
            "datetime",
            "home_team",
            "away_team",
            "home_goal",
            "away_goal",
            "season",
        ],
    },
    "Libertadores_Matches.csv": {
        "description": "Copa Libertadores fixtures 2013-2022 (stage labels)",
        "source": "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro",
        "license": "CC BY 4.0",
        "columns": [
            "datetime",
            "home_team",
            "away_team",
            "home_goal",
            "away_goal",
            "season",
            "stage",
        ],
    },
    "BR-Football-Dataset.csv": {
        "description": "Extended match statistics 2014-2023 (corners, shots, attacks)",
        "source": "https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches",
        "license": "CC0 Public Domain",
        "columns": [
            "tournament",
            "home",
            "away",
            "home_goal",
            "away_goal",
            "home_corner",
            "away_corner",
            "home_attack",
            "away_attack",
            "home_shots",
            "away_shots",
            "time",
            "date",
            "ht_result",
            "at_result",
            "total_corners",
        ],
    },
    "novo_campeonato_brasileiro.csv": {
        "description": "Historical Brasileirão 2003-2019 (stadium, winner, UF columns)",
        "source": "https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019",
        "license": "CC BY 4.0",
        "columns": [
            "ID",
            "Data",
            "Ano",
            "Rodada",
            "Equipe_mandante",
            "Equipe_visitante",
            "Gols_mandante",
            "Gols_visitante",
            "Mandante_UF",
            "Visitante_UF",
            "Vencedor",
            "Arena",
            "OBS",
        ],
    },
    "fifa_data.csv": {
        "description": "FIFA player database (18,207 players, ratings and attributes)",
        "source": "https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data",
        "license": "Apache 2.0",
        "columns": [
            "ID",
            "Name",
            "Age",
            "Nationality",
            "Overall",
            "Potential",
            "Club",
            "Position",
            "Jersey Number",
            "Value",
            "Wage",
            "Height",
            "Weight",
            "Crossing",
            "Finishing",
            "Dribbling",
            "...",
        ],
    },
}


def _jsonrpc_result(request_id, result: dict) -> dict:
    return {"jsonrpc": _JSONRPC_VERSION, "id": request_id, "result": result}


def _jsonrpc_error(request_id, code: int, message: str, data=None) -> dict:
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": _JSONRPC_VERSION, "id": request_id, "error": error}


class MCPServer:
    """Stateful MCP protocol handler (one instance per connection)."""

    def __init__(
        self, dataset: Dataset | None = None, dataset_loader=load_dataset
    ) -> None:
        self._dataset = dataset
        self._dataset_loader = dataset_loader
        self._initialized = False

    # -- dataset (lazy: the initialize handshake must be instant) ----------

    @property
    def dataset(self) -> Dataset:
        if self._dataset is None:
            self._dataset = self._dataset_loader()
        return self._dataset

    # -- protocol ----------------------------------------------------------

    def handle(self, message: object) -> dict | None:
        """
        Process one decoded JSON-RPC message.  Returns the response dict
        for requests, ``None`` for notifications (and for invalid input
        when no response is possible).  Batch arrays map to a list.
        """
        if isinstance(message, list):
            responses = [self.handle(entry) for entry in message]
            responses = [r for r in responses if r is not None]
            return responses or None
        if not isinstance(message, dict):
            return _jsonrpc_error(
                None, _INVALID_REQUEST, "Request must be a JSON object."
            )
        if message.get("jsonrpc") != _JSONRPC_VERSION:
            return _jsonrpc_error(
                message.get("id"), _INVALID_REQUEST, "jsonrpc must be '2.0'."
            )
        method = message.get("method")
        request_id = message.get("id")
        is_request = "id" in message
        params = message.get("params") or {}

        if not isinstance(method, str) or not method:
            return (
                _jsonrpc_error(
                    request_id, _INVALID_REQUEST, "Missing or invalid method."
                )
                if is_request
                else None
            )

        if not is_request:
            self._handle_notification(method, params)
            return None

        if method != "initialize" and not self._initialized:
            return _jsonrpc_error(
                request_id,
                _SERVER_NOT_INITIALIZED,
                "Server not initialized: call initialize first.",
            )

        handler = {
            "initialize": self._initialize,
            "ping": self._ping,
            "tools/list": self._tools_list,
            "tools/call": self._tools_call,
            "resources/list": self._resources_list,
            "resources/read": self._resources_read,
        }.get(method)

        if handler is None:
            return _jsonrpc_error(
                request_id, _METHOD_NOT_FOUND, f"Method not found: {method}"
            )
        try:
            return _jsonrpc_result(request_id, handler(params))
        except tools.ToolError as exc:
            return _jsonrpc_error(request_id, _INVALID_PARAMS, str(exc))
        except Exception as exc:  # noqa: BLE001 - protocol requires a reply
            # A JSON-RPC server must answer every request; unknown failures
            # become -32663 internal errors instead of killing the session.
            return _jsonrpc_error(
                request_id, _INTERNAL_ERROR, f"Internal error: {exc}", data=repr(exc)
            )

    # -- individual methods --------------------------------------------------

    def _handle_notification(self, method: str, params: dict) -> None:
        # Known client notifications; all are safely ignorable here.
        if method in {
            "notifications/initialized",
            "notifications/cancelled",
            "notifications/roots/list_changed",
            "notifications/progress",
            "notifications/message",
        }:
            if method == "notifications/initialized":
                self._initialized = True
            return

    def _initialize(self, params: dict) -> dict:
        requested = params.get("protocolVersion")
        protocol_version = (
            requested
            if requested in SUPPORTED_PROTOCOL_VERSIONS
            else DEFAULT_PROTOCOL_VERSION
        )
        self._initialized = True
        return {
            "protocolVersion": protocol_version,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
            },
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": INSTRUCTIONS,
        }

    def _ping(self, params: dict) -> dict:
        return {}

    def _tools_list(self, params: dict) -> dict:
        return {"tools": tools.TOOLS}

    def _tools_call(self, params: dict) -> dict:
        if not isinstance(params, dict) or "name" not in params:
            raise tools.ToolError("tools/call requires a 'name' parameter.")
        name = params["name"]
        if not isinstance(name, str) or not name:
            raise tools.ToolError("tools/call 'name' must be a non-empty string.")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise tools.ToolError("tools/call 'arguments' must be an object.")
        return tools.call_tool(self.dataset, name, arguments)

    # -- resources -----------------------------------------------------------

    def _resources_list(self, params: dict) -> dict:
        resources = [
            {
                "uri": "brazilian-soccer://overview",
                "name": "Dataset overview & schema",
                "description": "What is loaded, the graph model and "
                "team-name normalisation notes",
                "mimeType": "text/plain",
            },
            {
                "uri": "brazilian-soccer://competitions",
                "name": "Competitions index",
                "description": "Competitions with seasons and match counts",
                "mimeType": "text/plain",
            },
            {
                "uri": "brazilian-soccer://teams",
                "name": "Club directory",
                "description": "Every club with canonical id, state and matches",
                "mimeType": "text/plain",
            },
        ]
        for file_name, meta in _DATASET_META.items():
            resources.append(
                {
                    "uri": f"brazilian-soccer://dataset/{file_name}",
                    "name": f"Dataset: {file_name}",
                    "description": meta["description"],
                    "mimeType": "text/plain",
                }
            )
        return {"resources": resources}

    def _resources_read(self, params: dict) -> dict:
        if not isinstance(params, dict) or not params.get("uri"):
            raise tools.ToolError("resources/read requires a 'uri' parameter.")
        uri = str(params["uri"])
        if uri == "brazilian-soccer://overview":
            text = self._overview_text()
        elif uri == "brazilian-soccer://competitions":
            text = self._competitions_text()
        elif uri == "brazilian-soccer://teams":
            text = self._teams_text()
        elif uri.startswith("brazilian-soccer://dataset/"):
            file_name = uri.split("brazilian-soccer://dataset/", 1)[1]
            meta = _DATASET_META.get(file_name)
            if meta is None:
                raise tools.ToolError(f"Unknown dataset resource: {file_name}")
            text = self._dataset_text(file_name, meta)
        else:
            raise tools.ToolError(f"Unknown resource uri: {uri}")
        return {"contents": [{"uri": uri, "mimeType": "text/plain", "text": text}]}

    # -- resource bodies -----------------------------------------------------

    def _overview_text(self) -> str:
        ds = self.dataset
        played = sum(1 for m in ds.matches if m.played)
        matches_line = (
            f"Matches loaded: {len(ds.matches)} ({played} played) "
            f"across {len(ds.competition_matches)} competitions."
        )
        lines = [
            f"{SERVER_NAME} v{SERVER_VERSION} - Brazilian soccer knowledge graph",
            matches_line,
            f"Clubs: {len(ds.clubs)}. Players: {len(ds.players)} (FIFA database).",
            "",
            "Model: matches link two club nodes (canonical ids like 'flamengo|RJ');",
            "each match carries competition, season, date, score, round/stage,",
            "venue (2003-2019) and extended stats (corners/shots/attacks,",
            "2014-2023 subset). Player nodes carry FIFA ratings and link to clubs.",
            "",
            "Team-name normalisation: state suffixes ('Palmeiras-SP'), accents",
            "('Grêmio'/'Gremio'), full names ('Sport Club Corinthians Paulista'),",
            "aliases ('Atlético Mineiro' = 'Atletico-MG', 'Red Bull Bragantino'",
            "= 'Bragantino-SP') and stateless names resolved by dominance",
            "('Santos' -> Santos-SP). Dates: ISO, ISO+time and DD/MM/YYYY.",
            "",
            "Note: goals recorded as 'NA'/'-' mean scheduled-but-not-played;",
            "they appear in fixture lists but are excluded from all statistics.",
        ]
        return "\n".join(lines)

    def _competitions_text(self) -> str:
        ds = self.dataset
        lines = ["Competitions:"]
        for comp_id, meta in COMPETITIONS.items():
            matches = ds.competition_matches.get(comp_id, [])
            if not matches:
                continue
            seasons = ds.seasons_for(comp_id)
            lines.append(
                f"- {comp_id} ({meta['display']}): {len(matches)} matches, "
                f"seasons {seasons[0]}-{seasons[-1] if seasons else '?'}"
            )
        return "\n".join(lines)

    def _teams_text(self) -> str:
        ds = self.dataset
        lines = ["Clubs (canonical id: matches):"]
        for key in sorted(ds.clubs, key=lambda k: -ds.clubs[k].match_count):
            club = ds.clubs[key]
            lines.append(f"- {key}: {club.match_count} matches ({club.display})")
        return "\n".join(lines)

    def _dataset_text(self, file_name: str, meta: dict) -> str:
        ds = self.dataset
        if file_name == DATA_FILES["fifa"]:
            rows = len(ds.players)
        else:
            rows = sum(1 for m in ds.matches if m.source == file_name)
        lines = [
            f"Dataset: {file_name}",
            f"Description: {meta['description']}",
            f"Rows kept after cross-source dedup: {rows}",
            f"Columns: {', '.join(meta['columns'])}",
            f"Source: {meta['source']}",
            f"License: {meta['license']}",
        ]
        return "\n".join(lines)


# --------------------------------------------------------------------------
# stdio transport
# --------------------------------------------------------------------------


def _write_message(stream: TextIO, message: dict) -> None:
    stream.write(json.dumps(message, ensure_ascii=False) + "\n")
    stream.flush()


def serve(
    stdin: TextIO | BinaryIO | None = None, stdout: TextIO | BinaryIO | None = None
) -> None:
    """
    Run the stdio JSON-RPC loop until EOF.  Each message is one line of
    JSON; responses are written as single lines, flushed immediately.
    Parse errors are answered with -32700 (id null) per the spec.
    """
    if stdin is None:
        stdin = sys.stdin
    if stdout is None:
        stdout = sys.stdout

    server = MCPServer()
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            _write_message(
                stdout, _jsonrpc_error(None, _PARSE_ERROR, f"Parse error: {exc}")
            )
            continue
        response = server.handle(message)
        if response is not None:
            _write_message(stdout, response)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``python -m brazilian_soccer_mcp [--stdio] [--version]``."""
    parser = argparse.ArgumentParser(
        prog="brazilian-soccer-mcp",
        description="MCP server for Brazilian soccer data (stdio transport).",
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        default=True,
        help="serve MCP over stdin/stdout (default)",
    )
    parser.add_argument(
        "--version", action="version", version=f"{SERVER_NAME} {SERVER_VERSION}"
    )
    parser.parse_args(argv)  # handles --version/--help; no flags carry data
    serve()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
