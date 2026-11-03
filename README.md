# mcp-utcp-bench

Measuring MCP against UTCP instead of arguing about it.

Both protocols solve the same problem — telling an agent which tools exist and how
to call them — with opposite architectures. MCP routes every call through a server
speaking JSON-RPC; UTCP publishes a JSON *manual* and lets the agent call the tool
directly in its native protocol. Public comparisons are mostly diagrams and
opinions. This repository measures.

**Status: ten local tools.** One machine, loopback only. A remote API and
authentication are the next stage.

## Results

Measured 2026-11-03 on one machine (Linux, Python 3.14.9), loopback only. n=100
calls per tool after 10 warm-up calls, 50 re-discovery calls, 5 discovery runs.
Raw data in [`results/raw.csv`](results/raw.csv), table in
[`results/summary.md`](results/summary.md).

| tool | MCP p50 / p95 | UTCP p50 / p95 |
|---|---|---|
| `search_docs` (HTTP GET) | 2.59 / 2.70 ms | 1.09 / 1.15 ms |
| `read_file` (filesystem) | 2.77 / 2.87 ms | 1.13 / 1.17 ms |
| `list_dir` (filesystem) | 2.68 / 2.79 ms | 1.08 / 1.12 ms |
| `word_count` (compute) | 2.61 / 2.77 ms | 0.99 / 1.03 ms |
| `sqlite_query` (SQLite) | 3.12 / 3.20 ms | 1.32 / 1.34 ms |
| `json_filter` (compute) | 2.72 / 2.83 ms | 1.02 / 1.08 ms |
| `regex_extract` (compute) | 2.72 / 2.81 ms | 1.01 / 1.11 ms |
| `echo_json` (HTTP POST) | 2.73 / 2.81 ms | 1.01 / 1.07 ms |
| `slow_task` (50 ms server-side) | 58.64 / 58.86 ms | 54.17 / 54.41 ms |
| `sha256_text` (subprocess) | 19.49 / 20.09 ms | 21.75 / 22.50 ms |

| aggregate | MCP | UTCP |
|---|---|---|
| discovery, process start included | 906 ms | 2.3 ms |
| re-discovery at runtime, p50 | 1.60 ms | 0.48 ms |
| tool schema, minimal | 693 tokens | 545 tokens |

### What the numbers actually say

**Per-call overhead is small, and it is not where the debate says it is.** On the
eight tools that delegate to the same local service, MCP adds **1.5 to 1.8 ms** over
UTCP. That is the price of a JSON-RPC round trip through a second process. Anyone
claiming MCP is "orders of magnitude slower" is measuring something else — probably
a network call, or their own HTTP client (see pitfall 5).

**Tool cost dominates protocol cost.** `sha256_text` costs ~20 ms on both sides
because both spawn a subprocess, and MCP even wins slightly: UTCP's shell wrapper
costs more than the JSON-RPC hop. `slow_task` shows the same pattern at a larger
scale, with 4.5 ms of overhead on a 50 ms tool. Optimizing the transport of a call
whose cost is elsewhere buys nothing.

**Discovery is a start-up cost, not a protocol cost.** 906 ms is a Python
interpreter starting the MCP server; the handshake itself is the 1.60 ms line. A
long-lived session amortizes the former to zero. Quoting 906 ms as "MCP overhead"
would be dishonest, and it is the most misused number in this space.

**MCP carries more context here: 693 against 545 tokens.** The MCP SDK emits
generated JSON-Schema titles per argument (`search_docsArguments`, `Query`) and
per-tool framing the UTCP manual does not carry. With ten tools and compact schemas
that is a 27 % surcharge — small in absolute terms, but it scales with the number of
tools, which is where agent budgets break.

## Method

Ten tools, each implemented twice, with identical names, descriptions and input
schemas, all backed by the same local service (`bench/tools/api_server.py`) or the
same CLI. The only variable is the transport.

| kind | tools |
|---|---|
| HTTP GET | `search_docs`, `read_file`, `list_dir`, `word_count`, `sqlite_query`, `json_filter`, `regex_extract`, `slow_task` |
| HTTP POST | `echo_json` |
| subprocess | `sha256_text` |

- MCP: one `MCPServer` over stdio (`bench/mcp_server.py`), stdlib HTTP client.
- UTCP: one manual served at `GET /utcp`, ten call templates
  (`bench/manuals/tools.json`).

Two test suites protect the measurement:

- `tests/test_equivalence.py` — both implementations must return the same payload
  for the same input, on all ten tools.
- `tests/test_tool_surface.py` — the MCP schema and the UTCP manual must declare the
  same names, descriptions and parameters.

## Five pitfalls this benchmark caught

Recorded because they are the difference between a plausible number and a true one.

1. **Pydantic's `model_dump()` inflates the schema.** UTCP's input model serializes
   every optional field as `null`: 458 tokens instead of 110, a 3× overstatement of
   UTCP's context cost. Fixed with `exclude_none=True`.
2. **CLI placeholders are not `{arg}`.** In UTCP 1.x the CLI template substitutes
   `UTCP_ARG_<name>_UTCP_END`. With `{text}`, the literal string `{text}` is hashed and
   the benchmark silently measures the wrong thing.
3. **GET arguments are passed by name.** There is no `query_params` mapping field:
   leftover arguments become query parameters, so tool input names must match the
   API's parameter names.
4. **Tool names are namespaced by manual** (`local.search_docs`), while the manual's
   own `name` field does not appear in the tool list.
5. **The client library can be the bottleneck.** The first version of this benchmark
   reported 9.8 ms per MCP call. The cause was `httpx`: on a 50 ms endpoint it added
   27 ms against 1.5 ms for `http.client` and `urllib` on the same fixture. Switching
   the MCP server to the stdlib divided its latency by four. A comparison that does
   not control for the HTTP client measures the client, not the protocol.

## Limits

- One machine, one run, loopback. Latency numbers are indicative, not portable.
- All tools are local. A remote API adds variance this stage deliberately avoids —
  and would narrow the relative gap, since the network dominates both paths.
- The MCP server is trivial. A server doing real work would shift the balance.
- Token counts use `cl100k_base`; other tokenizers differ slightly.
- No authentication, no error paths, no streaming: those change the cost profile and
  are not covered here.

## Next

- A remote HTTP API with rate limits, to see how the gap behaves when latency is real.
- A long-lived MCP session, to separate start-up from per-call cost cleanly.
- Auth on both sides, and what each protocol makes you write for it.

## Run it

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

python -m pytest -q tests/     # equivalence + tool surface
python bench/harness.py        # writes results/raw.csv and results/summary.md
```

`make test` and `make bench` do the same where `make` is available.

MIT licensed.
