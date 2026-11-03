"""MCP server exposing the two benchmark tools over stdio.

Tool surface is intentionally identical to the UTCP manual: same names,
same descriptions, same input schemas. Any difference would measure the
wording, not the protocol.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import httpx
from mcp.server.mcpserver import MCPServer

API_URL = os.environ.get("BENCH_API_URL", "http://127.0.0.1:8765") + "/search"
CLI = Path(__file__).parent / "tools" / "cli_tool.py"

server = MCPServer("bench-slice")


@server.tool(description="Search the local document index and return up to five matches.")
def search_docs(query: str) -> dict:
    """Search documents by keyword."""
    response = httpx.get(API_URL, params={"query": query}, timeout=5.0)
    response.raise_for_status()
    return response.json()


@server.tool(description="Compute the SHA-256 digest of a text and return it as hex.")
def sha256_text(text: str) -> str:
    """Hash a string."""
    out = subprocess.run(
        [sys.executable, str(CLI), text],
        capture_output=True, text=True, timeout=5, check=True,
    )
    return out.stdout.strip()


if __name__ == "__main__":
    server.run(transport="stdio")
