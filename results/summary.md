| metric | MCP | UTCP |
|---|---|---|
| discovery, processus inclus (median) | 925.3 ms | 2.3 ms |
| redécouverte à chaud, p50 (n=50) | 1.64 ms | 0.48 ms |
| call `search_docs` p50/p95 | 2.68 / 2.78 ms (n=100) | 1.10 / 1.14 ms (n=100) |
| call `sha256_text` p50/p95 | 19.60 / 20.10 ms (n=100) | 21.67 / 22.51 ms (n=100) |
| call `read_file` p50/p95 | 3.01 / 3.12 ms (n=100) | 1.14 / 1.19 ms (n=100) |
| call `list_dir` p50/p95 | 3.01 / 3.10 ms (n=100) | 1.05 / 1.10 ms (n=100) |
| call `word_count` p50/p95 | 2.94 / 3.02 ms (n=100) | 1.00 / 1.05 ms (n=100) |
| call `sqlite_query` p50/p95 | 3.44 / 3.51 ms (n=100) | 1.38 / 1.46 ms (n=100) |
| call `json_filter` p50/p95 | 2.99 / 3.07 ms (n=100) | 1.01 / 1.09 ms (n=100) |
| call `regex_extract` p50/p95 | 3.00 / 3.08 ms (n=100) | 1.01 / 1.05 ms (n=100) |
| call `echo_json` p50/p95 | 3.00 / 3.09 ms (n=100) | 1.05 / 1.10 ms (n=100) |
| call `slow_task` p50/p95 | 58.55 / 58.80 ms (n=100) | 54.15 / 54.43 ms (n=100) |
| schéma minimal (tokens) | 693 | 545 |
| schéma complet côté client (tokens) | 703 | 545 |
