from setuptools import setup, find_packages

setup(
    name="brazilian-soccer-mcp",
    version="1.0.0",
    description="MCP server exposing a query interface over Brazilian soccer datasets.",
    packages=find_packages(exclude=("tests", "tests.*")),
    python_requires=">=3.10",
    install_requires=["mcp>=2.0"],
    entry_points={
        "console_scripts": [
            "brazilian-soccer-mcp = brazilian_soccer_mcp.mcp_server:main",
        ],
    },
)
