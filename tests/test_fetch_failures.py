"""
Failure-path tests for the network call sites that adopt http_get_with_retry.

The helper's own retry logic is covered in test_http_retry.py; these assert the
callers degrade correctly (return None / cache a not_found) on permanent and
exhausted-transient failures instead of crashing or misclassifying.
"""

import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import _collection_io as io
import coord_resolver as cr
import fetch_ext_ref as fer


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    # Skip the real backoff/politeness sleeps so failure paths run instantly.
    monkeypatch.setattr(io.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(cr.time, "sleep", lambda *_a, **_k: None)


def _raise(exc):
    def fake(req, timeout=None):
        raise exc
    return fake


def _http(code):
    return urllib.error.HTTPError("http://x", code, "err", {}, None)


# ── fetch_ext_ref._fetch_page ────────────────────────────────────────────────

def test_fetch_page_returns_none_on_404(monkeypatch):
    monkeypatch.setattr(io.urllib.request, "urlopen", _raise(_http(404)))
    assert fer._fetch_page("http://x") is None


def test_fetch_page_returns_none_after_exhausted_5xx(monkeypatch):
    calls = {"n": 0}

    def fake(req, timeout=None):
        calls["n"] += 1
        raise _http(503)

    monkeypatch.setattr(io.urllib.request, "urlopen", fake)
    assert fer._fetch_page("http://x") is None
    assert calls["n"] == 3  # retried before giving up


def test_fetch_page_succeeds_after_transient(monkeypatch):
    seq = [TimeoutError("slow"), None]

    class R:
        def read(self): return b"<html>hi</html>"
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake(req, timeout=None):
        eff = seq.pop(0)
        if eff is not None:
            raise eff
        return R()

    monkeypatch.setattr(io.urllib.request, "urlopen", fake)
    assert fer._fetch_page("http://x") == "<html>hi</html>"


# ── coord_resolver fetchers ──────────────────────────────────────────────────

def test_tcgdex_name_caches_not_found_on_404(monkeypatch):
    r = cr.CoordResolver(fetch=True, tcgdex_sets={"A1"})
    monkeypatch.setattr(io.urllib.request, "urlopen", _raise(_http(404)))
    assert r._tcgdex_name("A1", 9991) is None
    assert r.tcgdex_cache["A1-9991"]["error"] == "not_found"


def test_tcgdex_name_records_http_error_on_exhausted_5xx(monkeypatch):
    r = cr.CoordResolver(fetch=True, tcgdex_sets={"A1"})
    monkeypatch.setattr(io.urllib.request, "urlopen", _raise(_http(503)))
    assert r._tcgdex_name("A1", 9992) is None
    assert r.tcgdex_cache["A1-9992"]["error"] == "http_503"


def test_limitless_name_returns_none_on_failure(monkeypatch):
    r = cr.CoordResolver(fetch=True, tcgdex_sets={"A1"})
    monkeypatch.setattr(io.urllib.request, "urlopen", _raise(urllib.error.URLError("down")))
    assert r._limitless_name("A1", 9993) is None
    # cached so a later lookup in the same run doesn't refetch
    assert "A1/9993" in r.limitless_cache
