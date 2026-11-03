"""MCP server exposing the benchmark tools over stdio.

The tool surface is intentionally identical to the UTCP manual: same names,
same descriptions, same input schemas. `tests/test_tool_surface.py` enforces
that equality, because any divergence would measure wording, not protocol.

Every tool delegates to the same local service the UTCP manual points at, so
the only variable between the two implementations is the transport.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import json
import urllib.parse
import urllib.request

from mcp.server.mcpserver import MCPServer

BASE = os.environ.get("BENCH_API_URL", "http://127.0.0.1:8765")
CLI = Path(__file__).parent / "tools" / "cli_tool.py"
TIMEOUT = 10.0

server = MCPServer("mcp-utcp-bench")


def _get(route: str, **params) -> dict:
    """stdlib HTTP client on purpose: httpx added ~27 ms on this fixture,
    which would have been misread as MCP overhead."""
    url = f"{BASE}{route}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        return json.loads(response.read())


@server.tool(description="Search the local document index and return up to five matches.")
def search_docs(query: str) -> dict:
    return _get("/search", query=query)


@server.tool(description="Compute the SHA-256 digest of a text and return it as hex.")
def sha256_text(text: str) -> str:
    out = subprocess.run(
        [sys.executable, str(CLI), text],
        capture_output=True, text=True, timeout=TIMEOUT, check=True,
    )
    return out.stdout.strip()


@server.tool(description="Read a text file from the fixtures directory and return its first 2000 characters.")
def read_file(path: str) -> dict:
    return _get("/file", path=path)


@server.tool(description="List the files available in the fixtures directory.")
def list_dir() -> dict:
    return _get("/ls")


@server.tool(description="Count whitespace-separated words in a text.")
def word_count(text: str) -> dict:
    return _get("/wc", text=text)


@server.tool(description="Read up to N rows from the events table of the local SQLite database.")
def sqlite_query(limit: int) -> dict:
    return _get("/sqlite", limit=limit)


@server.tool(description="Filter records by an exact field value and return up to five matches.")
def json_filter(field: str, value: str) -> dict:
    return _get("/filter", field=field, value=value)


@server.tool(description="Extract up to fifty matches of a regular expression from a text.")
def regex_extract(pattern: str, text: str) -> dict:
    return _get("/regex", pattern=pattern, text=text)


@server.tool(description="Send a JSON object and receive it back with its top-level keys.")
def echo_json(payload: dict) -> dict:
    data = json.dumps(payload).encode()
    request = urllib.request.Request(f"{BASE}/echo", data=data,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read())


@server.tool(description="Wait for the requested number of milliseconds and confirm the delay.")
def slow_task(ms: int) -> dict:
    return _get("/slow", ms=ms)


if __name__ == "__main__":
    server.run(transport="stdio")
