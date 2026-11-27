"""PlayGenre sentences built by tools/ma_genre_sentences.py, matched with hassil."""

import sys
from pathlib import Path

import pytest
import yaml
from hassil import Intents, recognize_best

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from ma_genre_sentences import build, spoken  # noqa: E402

GENRES = [
    {"id": 47, "name": "Rock", "tracks": 9000},
    {"id": 15, "name": "Dance", "tracks": 204},
    {"id": 30, "name": "R&B", "tracks": 120},
    {"id": 31, "name": "Hip Hop", "tracks": 80},
    {"id": 99, "name": "Polka", "tracks": 2},
]


@pytest.fixture(scope="module")
def built():
    return build(GENRES, min_tracks=5)


@pytest.fixture(scope="module")
def intents(built):
    # With the pack's other sentences and HA's built-in search list, as in a live install.
    merged = {"language": "en", "intents": {}, "lists": {"search_query": {"wildcard": True}}}
    for p in sorted((ROOT / "custom_sentences" / "en").glob("*.yaml")):
        data = yaml.safe_load(p.read_text())
        merged["intents"].update(data.get("intents", {}))
        merged["lists"].update(data.get("lists", {}))
    merged["intents"].update(built[0]["intents"])
    merged["lists"].update(built[0]["lists"])
    return Intents.from_dict(merged)


def test_spoken_forms():
    assert spoken("R&B") == ["r and b", "r n b"]
    assert spoken("Hip-Hop") == ["hip hop"]


def test_min_tracks_drops_small_genres(built):
    outs = {v["out"] for v in built[0]["lists"]["genre"]["values"]}
    assert outs == {"Rock", "Dance", "R&B", "Hip Hop"}
    assert "polka" not in built[1]


@pytest.mark.parametrize(
    "text, genre",
    [
        ("play rock", "Rock"),
        ("could you play some dance music", "Dance"),
        ("put on some hip hop", "Hip Hop"),
        ("play r and b", "R&B"),
        ("I want to hear some rock music", "Rock"),
        ("can you please play dance songs", "Dance"),
    ],
)
def test_genre_beats_search(intents, text, genre):
    r = recognize_best(text, intents, language="en", intent_context={"area": "Den"})
    assert r is not None, f"no match: {text!r}"
    assert r.intent.name == "PlayGenre"
    assert r.entities["genre"].value == genre
    assert r.entities["area"].value == "Den"


@pytest.mark.parametrize("text", ["play Rock Lobster", "play Nina Simone", "play polka"])
def test_other_requests_still_search(intents, text):
    r = recognize_best(text, intents, language="en", intent_context={"area": "Den"})
    assert r is None or r.intent.name != "PlayGenre"


def test_jinja_map_is_case_insensitive(built):
    jinja = built[1]
    assert '"rock": "47"' in jinja and '"r and b": "30"' in jinja and '"r&b": "30"' in jinja
