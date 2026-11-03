"""Deterministic local service backing every benchmark tool.

Deliberately local: network variance would drown the protocol overhead this
benchmark is trying to isolate. A remote API is part of a later stage.

Every endpoint is a pure function of its input (fixed fixtures, fixed seeds) so
that both protocol implementations can be checked for equivalence.
"""
from __future__ import annotations

import json
import os
import re
import socket
import sqlite3
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
MANUAL = ROOT / "manuals" / "tools.json"
FIXTURES = ROOT / "fixtures"
DB_PATH = FIXTURES / "bench.db"

DOCS = [
    {"id": i, "title": f"Document {i} — {topic}", "body": f"Notes about {topic}."}
    for i, topic in enumerate(
        ["agents", "protocols", "evaluation", "latency", "tokens",
         "security", "tooling", "context", "retries", "observability"], start=1
    )
]

RECORDS = [
    {"id": i, "team": ["core", "platform", "security"][i % 3], "score": (i * 7) % 100}
    for i in range(1, 51)
]


def seed_db() -> None:
    if DB_PATH.exists():
        return
    FIXTURES.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, kind TEXT, amount INTEGER)")
    con.executemany(
        "INSERT INTO events VALUES (?, ?, ?)",
        [(i, ["read", "write", "delete"][i % 3], (i * 13) % 500) for i in range(1, 201)],
    )
    con.commit()
    con.close()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    # Nagle + delayed ACK added ~29 ms to small responses; that is a property of
    # the fixture server, not of any protocol under test. Disable it.
    disable_nagle_algorithm = True

    # ---- routing -------------------------------------------------------
    def setup(self) -> None:
        super().setup()
        # Nagle's algorithm + delayed ACK cost ~29 ms on small responses, which
        # would be misread as protocol overhead. Disable it on the server side.
        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        routes = {
            "/utcp": lambda: json.loads(MANUAL.read_text(encoding="utf-8")),
            "/search": lambda: self._search(q),
            "/file": lambda: self._read_file(q),
            "/ls": lambda: {"entries": sorted(p.name for p in FIXTURES.iterdir())[:100]},
            "/wc": lambda: {"words": len(re.findall(r"\S+", q.get("text", "")))},
            "/sqlite": lambda: self._sqlite(q),
            "/filter": lambda: {"matches": self._filter(q)},
            "/regex": lambda: {"matches": re.findall(q.get("pattern", r"\w+"), q.get("text", ""))[:50]},
            "/slow": lambda: self._slow(q),
        }
        if parsed.path not in routes:
            self._send(404, {"error": "not found"})
            return
        try:
            self._send(200, routes[parsed.path]())
        except Exception as exc:  # fixture errors must surface, not be swallowed
            self._send(400, {"error": f"{type(exc).__name__}: {exc}"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if parsed.path == "/echo":
            self._send(200, {"received": body, "keys": sorted(body.keys())})
            return
        self._send(404, {"error": "not found"})

    # ---- handlers ------------------------------------------------------
    def _search(self, q: dict) -> dict:
        query = (q.get("query") or q.get("q") or "").lower()
        hits = [d for d in DOCS if query in d["title"].lower()][:5] or DOCS[:1]
        return {"query": query, "count": len(hits), "results": hits}

    def _read_file(self, q: dict) -> dict:
        name = Path(q.get("path", "sample.txt")).name  # no traversal
        text = (FIXTURES / name).read_text(encoding="utf-8")
        return {"path": name, "chars": len(text), "content": text[:2000]}

    def _filter(self, q: dict) -> list:
        field = q.get("field", "team")
        value = q.get("value", "core")
        limit = int(q.get("limit", 5))
        return [r for r in RECORDS if str(r.get(field)) == value][:limit]

    def _sqlite(self, q: dict) -> dict:
        limit = int(q.get("limit", 10))
        con = sqlite3.connect(DB_PATH)
        rows = con.execute("SELECT id, kind, amount FROM events LIMIT ?", (limit,)).fetchall()
        con.close()
        return {"rows": [{"id": r[0], "kind": r[1], "amount": r[2]} for r in rows]}

    def _slow(self, q: dict) -> dict:
        ms = min(int(q.get("ms", 50)), 500)
        time.sleep(ms / 1000)
        return {"waited_ms": ms}

    # ---- plumbing ------------------------------------------------------
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
    seed_db()
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8765)
