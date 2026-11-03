"""Vercel serverless adapter for Flugel's existing Python API."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import server as flugel  # noqa: E402

# Vercel's deployed source tree is read-only. /tmp is writable, but ephemeral.
# This lets the demo accounts and API work on Vercel without changing local use.
flugel.DB_PATH = Path(os.environ.get("FLUGEL_DB_PATH", "/tmp/flugel.db"))
flugel.init_db()


class handler(flugel.Handler):
    """Route rewritten /api/* requests through the app's normal API handlers."""

    def _restore_api_path(self):
        rewritten_path = parse_qs(urlparse(self.path).query).get("path", [""])[0]
        self.path = "/api/" + rewritten_path.lstrip("/")

    def do_GET(self):
        self._restore_api_path()
        return super().do_GET()

    def do_POST(self):
        self._restore_api_path()
        return super().do_POST()

    def do_PATCH(self):
        self._restore_api_path()
        return super().do_PATCH()

    def do_DELETE(self):
        self._restore_api_path()
        return super().do_DELETE()
