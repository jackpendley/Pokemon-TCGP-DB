#!/usr/bin/env python3
"""
Unit tests for scripts/ingest_pz.py — the Pokémon Zone reference ingester.

Self-contained: a tiny synthetic pack-odds page (modelled on the real PZ markup)
is parsed and asserted, so the test never touches the network or a multi-MB .har.

    python3 -m pytest tests/test_ingest_pz.py
"""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import ingest_pz as ing


# A two-card pack-odds page in the exact shape PZ serves (figcaption name, a
# card-grid__pack_odds_slots table, and a "Drop Chance: N%" total). The second
# card has only 4 slot rows present (slot 5 must default to 0.0). A trailing
# "related" card link with NO odds block must be ignored.
_PAGE = """<html><head><title>Pulsing Aura Card List - Pulsing Aura (B3) - Pokémon TCG Pocket</title></head>
<body>
<div class="card-grid__cell">
  <a href="/cards/b3/1/tangela/"><img alt="Tangela Common - Pulsing Aura (B3) #1" /></a>
  <figcaption class="card-grid__cell-card-caption">Tangela</figcaption>
  <div class="card-grid__pack_odds_slots"><table>
    <tr><td>Card #1</td><td>1.54%</td></tr>
    <tr><td>Card #2</td><td>1.54%</td></tr>
    <tr><td>Card #3</td><td>1.54%</td></tr>
    <tr><td>Card #4</td><td>0%</td></tr>
    <tr><td>Card #5</td><td>0%</td></tr>
  </table></div>
  <div class="card-grid__pack_odds"><span>Drop Chance: 4.55%</span></div>
</div>
<div class="card-grid__cell">
  <a href="/cards/b3/234/bombirdier/"><img alt="Bombirdier Crown Rare - Pulsing Aura (B3) #234" /></a>
  <figcaption class="card-grid__cell-card-caption">Bombirdier</figcaption>
  <div class="card-grid__pack_odds_slots"><table>
    <tr><td>Card #4</td><td>0.02%</td></tr>
    <tr><td>Card #5</td><td>0.08%</td></tr>
  </table></div>
  <div class="card-grid__pack_odds"><span>Drop Chance: 0.1%</span></div>
</div>
<a href="/cards/b3/99/related-card/">a related-card link with no odds block</a>
</body></html>"""


def test_parse_pack_odds_page_basic():
    entry = ing.parse_pack_odds_page(_PAGE, "pulsing-aura")
    assert entry is not None
    assert entry["pack_name"] == "Pulsing Aura"
    assert entry["expansion_id"] == "B3"
    assert entry["pack_slug"] == "pulsing-aura"
    # The odds-less "related" link is excluded; only the two real cards count.
    assert entry["card_count"] == 2

    tangela = entry["cards"][0]
    assert tangela["card_url"] == "/cards/b3/1/tangela/"
    assert tangela["name"] == "Tangela"
    assert tangela["set_code"] == "B3"
    assert tangela["card_number"] == 1
    assert tangela["drop_chance_pct"] == 4.55
    assert tangela["slot_odds_pct"] == {"1": 1.54, "2": 1.54, "3": 1.54, "4": 0.0, "5": 0.0}


def test_missing_slots_default_to_zero():
    entry = ing.parse_pack_odds_page(_PAGE, "pulsing-aura")
    bomb = entry["cards"][1]
    assert bomb["card_number"] == 234
    assert bomb["drop_chance_pct"] == 0.1
    # Only slots 4 and 5 were present; 1–3 must be padded to 0.0.
    assert bomb["slot_odds_pct"] == {"1": 0.0, "2": 0.0, "3": 0.0, "4": 0.02, "5": 0.08}


def test_non_odds_page_returns_none():
    assert ing.parse_pack_odds_page("<html><body>no cards here</body></html>", "x") is None


def test_extract_pack_odds_from_har():
    """A minimal HAR envelope wrapping the synthetic page is parsed end-to-end."""
    har = {"log": {"entries": [{
        "request": {"url": "https://www.pokemon-zone.com/sets/b3/packs/pulsing-aura/"
                           "?show_pack_odds=1&show_pack_slot_odds=1"},
        "response": {"content": {"mimeType": "text/html", "text": _PAGE}},
    }]}}
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "capture.har"
        p.write_text(json.dumps(har), encoding="utf-8")
        odds = ing.extract_pack_odds(ing.responses_from_har(p))
    assert set(odds) == {"pulsing-aura"}
    assert odds["pulsing-aura"]["card_count"] == 2


def test_extract_pack_odds_is_source_agnostic():
    """The parser works on any (url, mimeType, body) responses — proving the live
    fetch path (which yields the same tuples) reuses identical parsing logic."""
    responses = [(
        "https://www.pokemon-zone.com/sets/b3/packs/pulsing-aura/"
        "?show_pack_odds=1&show_pack_slot_odds=1", "text/html", _PAGE)]
    odds = ing.extract_pack_odds(responses)
    assert set(odds) == {"pulsing-aura"}
    assert odds["pulsing-aura"]["cards"][0]["drop_chance_pct"] == 4.55
