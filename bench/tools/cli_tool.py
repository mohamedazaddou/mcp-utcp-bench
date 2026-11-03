"""Deterministic CLI tool: prints the SHA-256 of its argument."""
from __future__ import annotations

import hashlib
import sys

if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else ""
    print(hashlib.sha256(text.encode()).hexdigest())
