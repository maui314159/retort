"""Entry point for the Brazilian Soccer MCP server."""

from .server import mcp


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
