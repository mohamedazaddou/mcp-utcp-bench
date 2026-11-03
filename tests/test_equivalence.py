"""Both implementations must return the same thing for the same input.

A benchmark that measures two different behaviours is not a benchmark. These
tests exist because two silent measurement errors were caught by them: a CLI
placeholder that was never substituted, and a query parameter sent under the
wrong name.
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

# tool -> arguments, shared with the harness so both stay in sync
CASES = {
    "search_docs": {"query": "agent"},
    "sha256_text": {"text": "benchmark"},
    "read_file": {"path": "sample.txt"},
    "list_dir": {},
    "word_count": {"text": "one two three four five"},
    "sqlite_query": {"limit": 10},
    "json_filter": {"field": "team", "value": "core"},
    "regex_extract": {"pattern": r"\w+", "text": "alpha beta gamma"},
    "echo_json": {"payload": {"a": 1, "b": [1, 2, 3]}},
    "slow_task": {"ms": 10},
}


@pytest.fixture(scope="module")
def api():
    proc = subprocess.Popen([sys.executable, str(ROOT / "bench" / "tools" / "api_server.py"), str(PORT)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    yield API
    proc.terminate()


def _normalise(value):
    """Both clients may hand back a JSON string or an already-parsed object."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value.strip()
    return value


async def _via_mcp(tool: str, args: dict):
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, args)
            return _normalise(result.content[0].text)


async def _via_utcp(tool: str, args: dict):
    client = await UtcpClient.create(root_dir=str(ROOT), config=UTCP_CFG)
    try:
        await client.search_tools("")
        out = await client.call_tool(f"local.{tool}", args)
    finally:
        await client.close()
    return _normalise(out)


@pytest.mark.parametrize("tool", sorted(CASES))
def test_implementations_agree(api, tool):
    args = CASES[tool]
    mcp = asyncio.run(_via_mcp(tool, args))
    utcp = asyncio.run(_via_utcp(tool, args))
    assert mcp == utcp, f"{tool}: MCP={mcp!r} UTCP={utcp!r}"


def test_manual_is_valid_json():
    manual = json.loads((ROOT / "bench" / "manuals" / "tools.json").read_text(encoding="utf-8"))
    assert len(manual["tools"]) == len(CASES)
