"""Integration tests: real ThreadingHTTPServer + HTTP client."""
import json
import socket
import time
import urllib.request

import pytest

from app import make_server


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def server():
    port = _free_port()
    srv = make_server(host="127.0.0.1", port=port, db_path=":memory:")
    import threading

    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    # brief grace period for socket to be ready
    deadline = time.time() + 2.0
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.02)
    base = f"http://127.0.0.1:{port}"
    yield base
    srv.shutdown()
    srv.server_close()


def _request(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, (json.loads(raw) if raw else None)


def test_health(server):
    status, body = _request("GET", server + "/health")
    assert status == 200
    assert body == {"status": "ok"}


def test_full_crud_flow(server):
    # create
    status, book = _request("POST", server + "/books",
                            {"title": "Dune", "author": "Frank Herbert", "year": 1965})
    assert status == 201
    bid = book["id"]

    # get
    status, got = _request("GET", server + f"/books/{bid}")
    assert status == 200
    assert got["title"] == "Dune"

    # list with filter
    _request("POST", server + "/books",
             {"title": "1984", "author": "George Orwell", "year": 1949})
    status, books = _request("GET", server + "/books?author=George%20Orwell")
    assert status == 200
    assert len(books) == 1
    assert books[0]["title"] == "1984"

    # update
    status, updated = _request("PUT", server + f"/books/{bid}", {"year": 1966})
    assert status == 200
    assert updated["year"] == 1966

    # delete
    status, _ = _request("DELETE", server + f"/books/{bid}")
    assert status == 204
    status, _ = _request("GET", server + f"/books/{bid}")
    assert status == 404


def test_validation_returns_400(server):
    status, body = _request("POST", server + "/books", {"author": "No Title"})
    assert status == 400
    assert "error" in body


def test_missing_book_404(server):
    status, _ = _request("GET", server + "/books/9999")
    assert status == 404
