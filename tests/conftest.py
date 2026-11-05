"""Test setup: an isolated data folder and a local fixture website (no internet needed)."""
import http.server
import os
import socket
import tempfile
import threading
from pathlib import Path

import pytest

_DATA = tempfile.mkdtemp(prefix="backlink-mcp-test-")
os.environ["BACKLINK_MCP_DATA"] = _DATA  # must be set before backlink_mcp.server is imported
os.environ.pop("OPENPAGERANK_API_KEY", None)
for k in ("NO_PROXY", "no_proxy"):
    os.environ[k] = ",".join(x for x in (os.environ.get(k), "127.0.0.1", "localhost") if x)

FIXTURE = Path(__file__).parent / "fixture_site"


class _Handler(http.server.SimpleHTTPRequestHandler):
    def guess_type(self, path):
        p = str(path)
        if p.endswith(".xml"):
            return "application/xml"
        if p.endswith(".txt"):
            return "text/plain"
        if p.endswith(".js"):
            return "application/javascript"
        return "text/html"

    def log_message(self, *a):
        pass


@pytest.fixture(scope="session")
def site():
    """Serves tests/fixture_site on a free port. Files without an extension are HTML pages."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    root = Path(tempfile.mkdtemp(prefix="fixture-site-"))
    for f in FIXTURE.rglob("*"):
        if f.is_file():
            dest = root / f.relative_to(FIXTURE)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(f.read_text().replace("{{BASE}}", f"http://127.0.0.1:{port}"))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), lambda *a, **k: _Handler(*a, directory=str(root), **k))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield {"base": f"http://127.0.0.1:{port}", "domain": f"127.0.0.1:{port}", "root": root}
    srv.shutdown()


@pytest.fixture(scope="session")
def server():
    from backlink_mcp import server as s
    return s


@pytest.fixture(scope="session")
def code_dir():
    return Path(__file__).parent / "fixture_code"
