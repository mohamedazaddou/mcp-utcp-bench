| metric | MCP | UTCP |
|---|---|---|
| discovery, processus inclus (median) | 931.1 ms | 1.4 ms |
| redécouverte à chaud, p50 (n=50) | 1.24 ms | 0.09 ms |
| call `search_docs` p50/p95 | 9.80 / 10.97 ms (n=100) | 0.98 / 1.01 ms (n=100) |
| call `sha256_text` p50/p95 | 19.47 / 19.91 ms (n=100) | 20.11 / 20.58 ms (n=100) |
| schéma minimal (tokens) | 138 | 110 |
| schéma complet côté client (tokens) | 140 | 110 |
