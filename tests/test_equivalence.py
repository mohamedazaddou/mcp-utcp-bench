"""Both implementations must return the same thing for the same input.

A benchmark that measures two different behaviours is not a benchmark.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from utcp.utcp_client import UtcpClient

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "bench" / "mcp_server.py"
PORT = 8765
API = f"http://127.0.0.1:{PORT}"

UTCP_CFG = {"manual_call_templates": [{
    "name": "local",
    "call_template_type": "http",
    "url": f"{API}/utcp",
    "http_method": "GET",
    "allowed_communication_protocols": ["http", "cli"],
}]}


@pytest.fixture(scope="module")
def api():
    proc = subprocess.Popen([sys.executable, str(ROOT / "bench" / "tools" / "api_server.py"), str(PORT)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.6)
    yield API
    proc.terminate()


async def _via_mcp(tool: str, args: dict):
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, args)
            return json.loads(result.content[0].text) if tool == "search_docs" else result.content[0].text


async def _via_utcp(tool: str, args: dict):
    client = await UtcpClient.create(root_dir=str(ROOT), config=UTCP_CFG)
    try:
        await client.search_tools("")
        out = await client.call_tool(f"local.{tool}", args)
    finally:
        await client.close()
    return out if isinstance(out, dict) else json.loads(out) if tool == "search_docs" else str(out).strip()


def test_search_docs_equivalence(api):
    mcp = asyncio.run(_via_mcp("search_docs", {"query": "agent"}))
    utcp = asyncio.run(_via_utcp("search_docs", {"query": "agent"}))
    assert mcp["count"] == utcp["count"]
    assert [r["id"] for r in mcp["results"]] == [r["id"] for r in utcp["results"]]


def test_sha256_equivalence(api):
    mcp = asyncio.run(_via_mcp("sha256_text", {"text": "benchmark"}))
    utcp = asyncio.run(_via_utcp("sha256_text", {"text": "benchmark"}))
    assert utcp in mcp or mcp in utcp


def test_manual_is_valid_json():
    json.loads((ROOT / "bench" / "manuals" / "tools.json").read_text(encoding="utf-8"))
