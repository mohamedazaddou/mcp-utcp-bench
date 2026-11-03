"""Benchmark harness: MCP (stdio server) vs UTCP (manual + direct calls).

Slice scope: two local tools (HTTP + CLI), one machine, loopback only.
Everything here is instrumented; nothing is estimated.
"""
from __future__ import annotations

import asyncio
import csv
import json
import logging
import statistics
import subprocess
import sys
import time
from pathlib import Path

import tiktoken
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from utcp.utcp_client import UtcpClient

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "bench" / "mcp_server.py"
MANUAL = ROOT / "bench" / "manuals" / "tools.json"
API_PORT = 8765
API_URL = f"http://127.0.0.1:{API_PORT}"
CALLS = 100
WARMUP = 10
DISCOVERY_RUNS = 5

CALLS_SPEC = [
    ("search_docs", {"query": "agent"}),
    ("sha256_text", {"text": "benchmark"}),
]

logging.getLogger("utcp").setLevel(logging.CRITICAL)
logging.getLogger("utcp_http").setLevel(logging.CRITICAL)
ENC = tiktoken.get_encoding("cl100k_base")


def tokens(payload) -> int:
    return len(ENC.encode(json.dumps(payload, ensure_ascii=False)))


def pct(values: list[float], q: float) -> float:
    values = sorted(values)
    if not values:
        return 0.0
    k = (len(values) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


async def measure_mcp() -> dict:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    cfg = {"manual_call_templates": [{
        "name": "local",
        "call_template_type": "http",
        "url": f"{API_URL}/utcp",
        "http_method": "GET",
        "allowed_communication_protocols": ["http", "cli"],
    }]}

    # --- découverte : démarrage du processus + handshake + list_tools
    discovery = []
    schema = None
    for _ in range(DISCOVERY_RUNS):
        t0 = time.perf_counter()
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
        discovery.append((time.perf_counter() - t0) * 1000)
        schema = [t.model_dump(include={"name", "description", "input_schema"}) for t in listed.tools]

    # --- coût d'un list_tools à chaud (aller-retour protocole seul)
    warm_handshake = []

    # --- appels
    latencies = {name: [] for name, _ in CALLS_SPEC}
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for _ in range(50):
                t0 = time.perf_counter()
                await session.list_tools()
                warm_handshake.append((time.perf_counter() - t0) * 1000)
            for name, args in CALLS_SPEC:
                for _ in range(WARMUP):
                    await session.call_tool(name, args)
                for _ in range(CALLS):
                    t0 = time.perf_counter()
                    await session.call_tool(name, args)
                    latencies[name].append((time.perf_counter() - t0) * 1000)

    return {"discovery_ms": discovery, "warm_handshake_ms": warm_handshake,
            "latency_ms": latencies, "schema": schema}


async def measure_utcp() -> dict:
    cfg = {"manual_call_templates": [{
        "name": "local",
        "call_template_type": "http",
        "url": f"{API_URL}/utcp",
        "http_method": "GET",
        "allowed_communication_protocols": ["http", "cli"],
    }]}

    discovery = []
    schema = None
    for _ in range(DISCOVERY_RUNS):
        t0 = time.perf_counter()
        client = await UtcpClient.create(root_dir=str(ROOT), config=cfg)
        tools = await client.search_tools("")
        discovery.append((time.perf_counter() - t0) * 1000)
        schema = [{"name": t.name.split(".", 1)[-1], "description": t.description,
                   "inputs": (t.inputs.model_dump(exclude_none=True)
                              if hasattr(t.inputs, "model_dump") else t.inputs)}
                  for t in tools]
        await client.close()

    latencies = {name: [] for name, _ in CALLS_SPEC}
    client = await UtcpClient.create(root_dir=str(ROOT), config=cfg)
    warm_handshake = []
    for _ in range(50):
        t0 = time.perf_counter()
        await client.search_tools("")
        warm_handshake.append((time.perf_counter() - t0) * 1000)
    for name, args in CALLS_SPEC:
        for _ in range(WARMUP):
            await client.call_tool(f"local.{name}", args)
        for _ in range(CALLS):
            t0 = time.perf_counter()
            await client.call_tool(f"local.{name}", args)
            latencies[name].append((time.perf_counter() - t0) * 1000)
    await client.close()

    return {"discovery_ms": discovery, "warm_handshake_ms": warm_handshake,
            "latency_ms": latencies, "schema": schema}


async def main() -> None:
    api = subprocess.Popen([sys.executable, str(ROOT / "bench" / "tools" / "api_server.py"), str(API_PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.6)
    try:
        mcp = await measure_mcp()
        utcp = await measure_utcp()
    finally:
        api.terminate()

    rows = []
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    for impl, data in (("mcp", mcp), ("utcp", utcp)):
        for name, values in data["latency_ms"].items():
            for v in values:
                rows.append({"impl": impl, "tool": name, "metric": "call_ms", "value": round(v, 3)})
        for v in data["discovery_ms"]:
            rows.append({"impl": impl, "tool": "-", "metric": "discovery_ms", "value": round(v, 3)})
        for v in data["warm_handshake_ms"]:
            rows.append({"impl": impl, "tool": "-", "metric": "handshake_warm_ms", "value": round(v, 3)})
        minimal = [{"name": t["name"], "description": t["description"],
                    "inputs": t.get("inputs") or t.get("input_schema")} for t in data["schema"]]
        rows.append({"impl": impl, "tool": "-", "metric": "schema_tokens_min",
                     "value": tokens(minimal)})
        rows.append({"impl": impl, "tool": "-", "metric": "schema_tokens_full",
                     "value": tokens(data["schema"])})
        rows.append({"impl": impl, "tool": "-", "metric": "schema_bytes",
                     "value": len(json.dumps(data["schema"], ensure_ascii=False).encode())})

    with (out / "raw.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["impl", "tool", "metric", "value"])
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps({"mcp": mcp["schema"], "utcp": utcp["schema"]}, ensure_ascii=False, indent=1)[:400])
    lines = ["| metric | MCP | UTCP |", "|---|---|---|"]
    def fmt(vals):
        return f"{pct(vals, .5):.2f} / {pct(vals, .95):.2f} ms (n={len(vals)})"
    lines.append(f"| discovery, processus inclus (median) | {statistics.median(mcp['discovery_ms']):.1f} ms | {statistics.median(utcp['discovery_ms']):.1f} ms |")
    if mcp["warm_handshake_ms"]:
        lines.append(f"| redécouverte à chaud, p50 (n=50) | {pct(mcp['warm_handshake_ms'], .5):.2f} ms | {pct(utcp['warm_handshake_ms'], .5):.2f} ms |")
    for name, _ in CALLS_SPEC:
        lines.append(f"| call `{name}` p50/p95 | {fmt(mcp['latency_ms'][name])} | {fmt(utcp['latency_ms'][name])} |")
    mcp_min = [{"name": t["name"], "description": t["description"], "inputs": t.get("inputs") or t.get("input_schema")} for t in mcp["schema"]]
    utcp_min = [{"name": t["name"], "description": t["description"], "inputs": t.get("inputs") or t.get("input_schema")} for t in utcp["schema"]]
    lines.append(f"| schéma minimal (tokens) | {tokens(mcp_min)} | {tokens(utcp_min)} |")
    lines.append(f"| schéma complet côté client (tokens) | {tokens(mcp['schema'])} | {tokens(utcp['schema'])} |")
    print("\n".join(lines))
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
