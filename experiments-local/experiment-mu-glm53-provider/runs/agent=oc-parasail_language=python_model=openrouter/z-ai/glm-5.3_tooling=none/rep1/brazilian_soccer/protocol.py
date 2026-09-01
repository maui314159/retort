"""MCP protocol layer: JSON-RPC 2.0 over stdio, per the MCP specification.

Context: the server speaks the Model Context Protocol on stdin/stdout with
newline-delimited JSON-RPC 2.0 messages. It supports the core protocol
surface an MCP client needs: initialize handshake, ping, tools/list,
tools/call, resources/list and resources/read. Only protocol output is
written to stdout (diagnostics go to stderr), because the transport is
line-delimited and anything else would corrupt framing.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import TextIO

from .queries import QueryError

logger = logging.getLogger("brazilian_soccer.protocol")

JSONRPC_VERSION = "2.0"
SUPPORTED_PROTOCOL_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18")
DEFAULT_PROTOCOL_VERSION = "2024-11-05"

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class MCPStdioServer:
    """Serves MCP requests (tools, resources) from a repository over stdio."""

    def __init__(
        self,
        server_name: str,
        server_version: str,
        tools: list[dict],
        resources: list[dict] | None = None,
        instructions: str | None = None,
    ) -> None:
        self.server_name = server_name
        self.server_version = server_version
        self.tools = tools
        self.resources = resources or []
        self.instructions = instructions
        self._resources_by_uri = {resource["uri"]: resource for resource in self.resources}

    # ------------------------------------------------------------------ loop

    def run(self, stdin: TextIO | None = None, stdout: TextIO | None = None) -> None:
        """Read newline-delimited JSON-RPC messages until stdin closes."""
        stream_in = stdin or sys.stdin
        stream_out = stdout or sys.stdout
        for line in stream_in:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError as error:
                self._write(stream_out, self._error(None, PARSE_ERROR, f"Parse error: {error}"))
                continue
            if isinstance(message, list):
                for item in message:
                    self._handle(item, stream_out)
            else:
                self._handle(message, stream_out)

    def _handle(self, message, stream_out) -> None:
        if not isinstance(message, dict) or "method" not in message:
            self._write(stream_out, self._error(message.get("id") if isinstance(message, dict) else None,
                                                INVALID_REQUEST, "Invalid Request"))
            return
        method = message.get("method")
        message_id = message.get("id")
        is_request = "id" in message
        params = message.get("params") or {}
        if not is_request:
            self._handle_notification(method, params)
            return
        try:
            result = self._dispatch(method, params)
        except _MethodNotFound as error:
            self._write(stream_out, self._error(message_id, METHOD_NOT_FOUND, str(error)))
            return
        except _InvalidParams as error:
            self._write(stream_out, self._error(message_id, INVALID_PARAMS, str(error)))
            return
        except Exception as error:  # pragma: no cover - defensive
            logger.exception("Unhandled error while processing %s", method)
            self._write(stream_out, self._error(message_id, INTERNAL_ERROR, f"Internal error: {error}"))
            return
        if result is not None:
            self._write(stream_out, {"jsonrpc": JSONRPC_VERSION, "id": message_id, "result": result})

    def _handle_notification(self, method: str, params: dict) -> None:
        logger.debug("Notification %s ignored", method)

    # -------------------------------------------------------------- dispatch

    def _dispatch(self, method: str, params: dict):
        if method == "initialize":
            return self._initialize(params)
        if method == "ping":
            return {}
        if method == "tools/list":
            return self._tools_list()
        if method == "tools/call":
            return self._tools_call(params)
        if method == "resources/list":
            return {"resources": self.resources}
        if method == "resources/read":
            return self._resources_read(params)
        if method == "prompts/list":
            return {"prompts": []}
        if method == "logging/setLevel":
            return {}
        raise _MethodNotFound(f"Method not found: {method}")

    def _initialize(self, params: dict) -> dict:
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else DEFAULT_PROTOCOL_VERSION
        capabilities = {
            "tools": {"listChanged": False},
            "resources": {"listChanged": False},
            "logging": {},
        }
        return {
            "protocolVersion": version,
            "capabilities": capabilities,
            "serverInfo": {
                "name": self.server_name,
                "version": self.server_version,
            },
            "instructions": self.instructions,
        }

    def _tools_list(self) -> dict:
        return {
            "tools": [
                {
                    "name": entry["name"],
                    "description": entry["description"],
                    "inputSchema": entry["inputSchema"],
                }
                for entry in self.tools
            ]
        }

    def _tools_call(self, params: dict) -> dict:
        name = params.get("name")
        if not isinstance(name, str) or not name:
            raise _InvalidParams("tools/call requires a tool name")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise _InvalidParams("tools/call arguments must be an object")
        for entry in self.tools:
            if entry["name"] == name:
                try:
                    result = entry["handler"](arguments)
                except QueryError as error:
                    return self._text_result(str(error), is_error=True)
                except TypeError as error:
                    raise _InvalidParams(f"Invalid arguments for tool '{name}': {error}") from error
                return self._json_result(result)
        raise _InvalidParams(f"Unknown tool: {name}")

    def _resources_read(self, params: dict) -> dict:
        uri = params.get("uri")
        resource = self._resources_by_uri.get(uri)
        if resource is None:
            raise _InvalidParams(f"Unknown resource: {uri!r}")
        return {"contents": [resource["_content"]()]}

    # ---------------------------------------------------------------- output

    @staticmethod
    def _text_result(text: str, is_error: bool = False) -> dict:
        result = {"content": [{"type": "text", "text": text}]}
        if is_error:
            result["isError"] = True
        return result

    def _json_result(self, payload) -> dict:
        text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        return self._text_result(text)

    @staticmethod
    def _error(message_id, code: int, message: str) -> dict:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": message_id,
            "error": {"code": code, "message": message},
        }

    @staticmethod
    def _write(stream_out, payload: dict) -> None:
        stream_out.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        stream_out.flush()


class _MethodNotFound(Exception):
    """JSON-RPC method-not-found (-32601)."""


class _InvalidParams(Exception):
    """JSON-RPC invalid-params (-32602)."""


def build_dataset_resources(repo) -> list[dict]:
    """Expose per-dataset summary resources for resources/list & read."""
    descriptions = {
        "Brasileirao_Matches.csv": "Brasileirão Serie A matches 2012-2022 with rounds",
        "Brazilian_Cup_Matches.csv": "Copa do Brasil matches 2012-2021 with rounds",
        "Libertadores_Matches.csv": "Copa Libertadores matches 2013-2022 with stages",
        "BR-Football-Dataset.csv": "Brazilian matches 2014-2023 with corners/shots/attacks statistics",
        "novo_campeonato_brasileiro.csv": "Historical Brasileirão 2003-2019 with stadiums",
        "fifa_data.csv": "FIFA player database (18k+ players)",
    }
    resources = []
    for filename, description in descriptions.items():
        slug = filename.replace(".csv", "").lower().replace("-", "_").replace(" ", "_")

        def _content(filename=filename, description=description) -> dict:
            summary = repo.load_report["files"].get(filename, {})
            sample_matches = [
                match.to_dict()
                for match in repo.matches
                if match.source == filename
            ][:3] or None
            if filename == "fifa_data.csv":
                body = {
                    "file": filename,
                    "description": description,
                    "rows": summary.get("rows"),
                    "loaded_players": summary.get("loaded"),
                    "sample_players": [player.to_dict() for player in repo.players[:3]],
                }
            else:
                body = {
                    "file": filename,
                    "description": description,
                    "rows": summary.get("rows"),
                    "loaded_matches": summary.get("loaded"),
                    "sample_matches": sample_matches,
                }
            return {
                "uri": f"soccer://datasets/{slug}",
                "mimeType": "application/json",
                "text": json.dumps(body, ensure_ascii=False, default=str),
            }

        resources.append(
            {
                "uri": f"soccer://datasets/{slug}",
                "name": filename,
                "description": description,
                "mimeType": "application/json",
                "_content": _content,
            }
        )
    resources.append(
        {
            "uri": "soccer://competitions",
            "name": "Competitions overview",
            "description": "Seasons, sources and match counts per competition",
            "mimeType": "application/json",
            "_content": lambda: {
                "uri": "soccer://competitions",
                "mimeType": "application/json",
                "text": json.dumps(
                    _competitions_body(repo), ensure_ascii=False, default=str
                ),
            },
        }
    )
    return resources


def _competitions_body(repo) -> dict:
    body = {"competitions": []}
    for name, entry in sorted(repo.competition_info.items()):
        body["competitions"].append(
            {
                "competition": name,
                "total_matches": entry["total_matches"],
                "seasons": {
                    str(season): info
                    for season, info in sorted(entry["seasons"].items())
                },
            }
        )
    return body
