"""The two surfaces must be identical, otherwise the benchmark measures wording.

MCP declares tools in Python decorators; UTCP declares them in JSON. Nothing
forces them to stay in sync, so this test does.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "bench" / "mcp_server.py"
MANUAL = ROOT / "bench" / "manuals" / "tools.json"


def _mcp_surface() -> dict[str, dict]:
    async def run():
        params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.list_tools()

    listed = asyncio.run(run())
    out = {}
    for tool in listed.tools:
        schema = tool.input_schema or {}
        out[tool.name] = {
            "description": (tool.description or "").strip(),
            "required": sorted(schema.get("required", [])),
            "properties": sorted((schema.get("properties") or {}).keys()),
        }
    return out


def _utcp_surface() -> dict[str, dict]:
    manual = json.loads(MANUAL.read_text(encoding="utf-8"))
    out = {}
    for tool in manual["tools"]:
        inputs = tool.get("inputs") or {}
        out[tool["name"]] = {
            "description": tool["description"].strip(),
            "required": sorted(inputs.get("required", [])),
            "properties": sorted((inputs.get("properties") or {}).keys()),
        }
    return out


def test_same_tool_names():
    assert sorted(_mcp_surface()) == sorted(_utcp_surface())


def test_same_descriptions_and_parameters():
    mcp, utcp = _mcp_surface(), _utcp_surface()
    differences = {name: (mcp[name], utcp[name]) for name in mcp if mcp[name] != utcp[name]}
    assert not differences, f"tool surfaces diverge: {differences}"
