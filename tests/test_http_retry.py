"""
Tests for _collection_io.http_get_with_retry — the shared network helper that
retries transient failures with exponential backoff instead of silently
swallowing them.
"""

import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import _collection_io as io


class _FakeResp:
    def __init__(self, body):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _patch_urlopen(monkeypatch, side_effects):
    """side_effects: list of either bytes (return) or Exception (raise)."""
    calls = {"n": 0}

    def fake(req, timeout=None):
        i = calls["n"]
        calls["n"] += 1
        eff = side_effects[i]
        if isinstance(eff, Exception):
            raise eff
        return _FakeResp(eff)

    monkeypatch.setattr(io.urllib.request, "urlopen", fake)
    return calls


def _http(code):
    return urllib.error.HTTPError("http://x", code, "err", {}, None)


def test_success_first_try(monkeypatch):
    calls = _patch_urlopen(monkeypatch, [b"OK"])
    assert io.http_get_with_retry("http://x", sleep=lambda d: None) == b"OK"
    assert calls["n"] == 1


def test_retries_then_succeeds(monkeypatch):
    calls = _patch_urlopen(monkeypatch, [TimeoutError("slow"), _http(503), b"OK"])
    slept = []
    out = io.http_get_with_retry("http://x", retries=3, backoff=0.5,
                                 backoff_factor=2.0, sleep=slept.append)
    assert out == b"OK"
    assert calls["n"] == 3
    assert slept == [0.5, 1.0]  # exponential backoff between the three attempts


def test_404_raises_immediately_without_retry(monkeypatch):
    calls = _patch_urlopen(monkeypatch, [_http(404), b"OK"])
    with pytest.raises(urllib.error.HTTPError) as exc:
        io.http_get_with_retry("http://x", retries=3, sleep=lambda d: None)
    assert exc.value.code == 404
    assert calls["n"] == 1


def test_429_is_retried(monkeypatch):
    calls = _patch_urlopen(monkeypatch, [_http(429), b"OK"])
    assert io.http_get_with_retry("http://x", sleep=lambda d: None) == b"OK"
    assert calls["n"] == 2


def test_exhaustion_reraises_last_transient(monkeypatch):
    calls = _patch_urlopen(monkeypatch, [_http(500), _http(502), _http(503)])
    with pytest.raises(urllib.error.HTTPError) as exc:
        io.http_get_with_retry("http://x", retries=3, backoff=0.01, sleep=lambda d: None)
    assert exc.value.code == 503
    assert calls["n"] == 3


def test_connection_error_retried_then_reraised(monkeypatch):
    calls = _patch_urlopen(monkeypatch, [urllib.error.URLError("down")] * 2)
    with pytest.raises(urllib.error.URLError):
        io.http_get_with_retry("http://x", retries=2, backoff=0.01, sleep=lambda d: None)
    assert calls["n"] == 2
