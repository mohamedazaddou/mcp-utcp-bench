| metric | MCP | UTCP |
|---|---|---|
| discovery, processus inclus (median) | 917.8 ms | 1.5 ms |
| redécouverte à chaud, p50 (n=50) | 1.30 ms | 0.10 ms |
| call `search_docs` p50/p95 | 9.86 / 10.90 ms (n=100) | 1.00 / 1.04 ms (n=100) |
| call `sha256_text` p50/p95 | 19.43 / 20.03 ms (n=100) | 20.22 / 20.46 ms (n=100) |
| schéma minimal (tokens) | 138 | 110 |
| schéma complet côté client (tokens) | 140 | 110 |
