"""Allow ``python -m brasil_mcp`` to run the CLI and ``python -m brasil_mcp.server`` the server."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
