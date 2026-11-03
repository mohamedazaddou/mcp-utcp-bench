| metric | MCP | UTCP |
|---|---|---|
| discovery, process start included (median) | 930.2 ms | 2.3 ms |
| re-discovery at runtime, p50 (n=50) | 1.53 ms | 0.48 ms |
| call `search_docs` p50/p95 | 2.67 / 2.75 ms (n=100) | 1.08 / 1.12 ms (n=100) |
| call `sha256_text` p50/p95 | 19.57 / 22.94 ms (n=100) | 21.73 / 22.51 ms (n=100) |
| call `read_file` p50/p95 | 2.69 / 2.83 ms (n=100) | 1.12 / 1.17 ms (n=100) |
| call `list_dir` p50/p95 | 2.64 / 2.95 ms (n=100) | 1.04 / 1.08 ms (n=100) |
| call `word_count` p50/p95 | 2.93 / 3.03 ms (n=100) | 0.98 / 1.02 ms (n=100) |
| call `sqlite_query` p50/p95 | 3.45 / 3.54 ms (n=100) | 1.31 / 1.33 ms (n=100) |
| call `json_filter` p50/p95 | 3.00 / 3.06 ms (n=100) | 1.00 / 1.07 ms (n=100) |
| call `regex_extract` p50/p95 | 2.99 / 3.06 ms (n=100) | 1.01 / 1.10 ms (n=100) |
| call `echo_json` p50/p95 | 3.00 / 3.06 ms (n=100) | 0.99 / 1.03 ms (n=100) |
| call `slow_task` p50/p95 | 58.48 / 58.75 ms (n=100) | 54.19 / 54.38 ms (n=100) |
| tool schema, minimal (tokens) | 693 | 545 |
| tool schema, full client-side (tokens) | 703 | 545 |
