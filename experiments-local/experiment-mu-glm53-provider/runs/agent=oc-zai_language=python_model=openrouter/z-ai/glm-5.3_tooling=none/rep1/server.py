"""
Entrypoint for the Brazilian Soccer MCP server (stdio transport).

Context (Why): TASK.md specifies an MCP server that an LLM client launches
and talks to over stdio; clients configure this file as the command.

What: delegates to brazilian_soccer_mcp.server.main(). Run directly:
    python server.py
or reference in an MCP client config:
    {"mcpServers": {"brazilian-soccer": {"command": "python", "args": ["<abs>/server.py"]}}}

Test: tests/test_server.py boots the same server object in-memory.
"""

from brazilian_soccer_mcp.server import main

if __name__ == "__main__":
    main()
