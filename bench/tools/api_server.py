"""Deterministic local REST API used as the HTTP tool in the benchmark.

Deliberately local: network variance would drown the protocol overhead we
are trying to measure. A remote API is part of the full version, not the slice.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

MANUAL = Path(__file__).resolve().parent.parent / "manuals" / "tools.json"

DOCS = [
    {"id": i, "title": f"Document {i} — {topic}", "body": f"Notes about {topic}."}
    for i, topic in enumerate(
        ["agents", "protocols", "evaluation", "latency", "tokens",
         "security", "tooling", "context", "retries", "observability"], start=1
    )
]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/utcp":
            self._send(200, json.loads(MANUAL.read_text(encoding="utf-8")))
            return
        if parsed.path != "/search":
            self._send(404, {"error": "not found"})
            return
        params = parse_qs(parsed.query)
        query = (params.get("query") or params.get("q") or [""])[0].lower()
        hits = [d for d in DOCS if query in d["title"].lower()][:5] or DOCS[:1]
        self._send(200, {"query": query, "count": len(hits), "results": hits})

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args) -> None:
        if os.environ.get("BENCH_VERBOSE"):
            sys.stderr.write((fmt % args) + "\n")


def serve(port: int = 8765) -> None:
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    import sys
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8765)
