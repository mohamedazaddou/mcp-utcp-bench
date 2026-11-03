# mcp-utcp-bench

Measuring MCP against UTCP instead of arguing about it.

Both protocols solve the same problem — telling an agent which tools exist and how
to call them — with opposite architectures. MCP routes every call through a server
speaking JSON-RPC; UTCP publishes a JSON *manual* and lets the agent call the tool
directly in its native protocol. The public comparisons are mostly diagrams and
opinions. This repository measures.

**Status: vertical slice.** Two local tools, one machine, loopback only. The full
version targets ten tools, including a remote HTTP API.

## Results

Measured on 2026-11-03, one machine (Linux, Python 3.14.9), localhost only,
n=100 calls per tool after 10 warm-up calls, 50 re-discovery calls, 5 discovery runs.

| metric | MCP | UTCP |
|---|---|---|
| discovery, process included (median) | 931 ms | 1.4 ms |
| re-discovery at runtime, p50 (n=50) | 1.24 ms | 0.09 ms |
| call `search_docs` p50 / p95 | 9.80 / 10.97 ms | 0.98 / 1.01 ms |
| call `sha256_text` p50 / p95 | 19.47 / 19.91 ms | 20.11 / 20.58 ms |
| tool schema, minimal (tokens) | 138 | 110 |
| tool schema, full client-side (tokens) | 140 | 110 |

Raw data: [`results/raw.csv`](results/raw.csv) (regenerated locally, not committed).

### What the numbers actually say

**Discovery is not a protocol cost.** The 931 ms for MCP is almost entirely Python
interpreter start-up for the server process. The protocol handshake itself is the
1.24 ms line. Quoting 931 ms as "MCP overhead" would be dishonest; the honest
statement is that a stdio server pays a process start-up once per session, and
that a long-lived connection amortizes it to nothing.

**The HTTP tool is where the architectures really differ.** 9.8 ms against 0.98 ms
is a tenfold gap, and it is structural: MCP makes the call travel
agent → JSON-RPC → server → HTTP → API → back, while UTCP calls the API directly.
On a local loopback the extra hop is cheap in absolute terms; over a network with
real latency, the ratio narrows, because the network dominates both paths.

**Where the protocol is not the bottleneck, it changes nothing.** `sha256_text`
costs the same on both sides (~20 ms), because both spawn a Python subprocess. The
tool dominates, not the transport. This is the least photogenic result and probably
the most useful one: choosing a protocol to optimize a call whose cost is elsewhere
buys nothing.

**UTCP was cheaper in context, not more expensive.** 110 tokens against 138, because
the MCP SDK emits generated JSON-Schema titles (`search_docsArguments`, `Query`)
that UTCP's manual does not carry. The gap is small and would reverse with richer
schemas — but it contradicts the common claim that describing calls as data costs
more context than describing them as a protocol.

## Method

Two tools, implemented twice, with identical names, descriptions and input schemas:

| tool | implementation | call path |
|---|---|---|
| `search_docs` | local REST API (`bench/tools/api_server.py`) | HTTP GET |
| `sha256_text` | local CLI (`bench/tools/cli_tool.py`) | subprocess |

- MCP: one `MCPServer` over stdio, exposing both tools (`bench/mcp_server.py`).
- UTCP: one manual served at `GET /utcp`, two call templates (`bench/manuals/tools.json`).

`tests/test_equivalence.py` asserts that both implementations return the same
payload for the same input. A benchmark that measures two different behaviours
measures nothing.

## Four pitfalls this slice already hit

Recorded because they are the difference between a plausible number and a true one.

1. **Pydantic's `model_dump()` inflates the schema.** UTCP's input model serializes
   every optional field as `null`, producing 458 tokens instead of 110 — a 3×
   overstatement of UTCP's context cost. Fixed with `exclude_none=True`.
2. **CLI placeholders are not `{arg}`.** In UTCP 1.x the CLI template substitutes
   `UTCP_ARG_<name>_UTCP_END`. With `{text}`, the literal string `{text}` is hashed
   and the benchmark silently measures the wrong thing. The equivalence test caught it.
3. **GET arguments are passed by name.** There is no `query_params` mapping field:
   leftover arguments become query parameters, so the tool's input names must match
   the API's parameter names.
4. **Tool names are namespaced by manual** (`local.search_docs`), while the manual's
   own `name` field is absent from the model list.

## Limits

- One machine, one run, loopback. Latency numbers are indicative, not portable.
- Two tools out of ten; both local. A remote API adds variance this slice avoids
  on purpose.
- The MCP server is trivial. A server that does real work would shift the balance
  between the two sides.
- Token counts use `cl100k_base`; other tokenizers will differ slightly.

## Next

- Eight more tools, including a remote HTTP API with rate limits.
- A long-lived MCP session, to separate start-up cost from per-call cost properly.
- Auth on both sides, and what each protocol makes you write for it.

## Run it

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

python -m pytest -q tests/     # both implementations must agree
python bench/harness.py        # writes results/raw.csv and results/summary.md
```

`make test` and `make bench` do the same thing where `make` is available.

MIT licensed.
