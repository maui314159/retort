"""Entry point: `python -m brazilian_soccer_mcp` runs the stdio MCP server."""

from .server import create_server


def main() -> None:
    server = create_server()
    server.run("stdio")


if __name__ == "__main__":
    main()
