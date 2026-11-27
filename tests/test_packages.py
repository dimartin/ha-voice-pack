"""The intent scripts in packages/, checked against the sentences that fill them.

Home Assistant offers every intent script to an LLM agent as a tool, with a fixed
parameter set (name, area, floor, domain, device_class) whatever slots the sentences
fill. A script that needs any other slot gets called with nothing in it ("is it going
to rain tomorrow?" with no day), so it must be voice only: `platforms: [conversation]`.
"""

import re
import sys

import yaml

from conftest import ROOT, sentence_files

sys.path.insert(0, str(ROOT / "tools"))
from ma_genre_sentences import build  # noqa: E402

# What HA's ScriptIntentHandler.slot_schema can carry (intent_script/helpers.py).
TOOL_SLOTS = {"name", "area", "floor", "domain", "device_class", "preferred_area_id", "preferred_floor_id"}


def _scripts():
    out = {}
    for p in sorted((ROOT / "packages").glob("*.yaml")):
        out.update((yaml.safe_load(p.read_text()) or {}).get("intent_script") or {})
    return out


def _slots():
    """intent name -> every slot its sentences can fill, including fixed `slots:`."""
    intents = {}
    for data in sentence_files().values():
        intents.update(data.get("intents", {}))
    intents.update(build([{"id": 1, "name": "Rock", "tracks": 9}], min_tracks=1)[0]["intents"])
    out = {}
    for name, intent in intents.items():
        found = set()
        for block in intent["data"]:
            for sentence in block["sentences"]:
                slots = re.findall(r"\{([a-z_:]+)\}", sentence)
                # A slot this pattern can't read would be missed silently, and its
                # script could stay exposed; so every brace must be one it read.
                assert sentence.count("{") == len(slots), f"unparsed slot in {sentence!r}"
                assert "<" not in sentence, f"expansion rule in {sentence!r}: read its slots too"
                found |= {m.split(":")[-1] for m in slots}
            found |= set(block.get("slots", {}))
            found |= set(block.get("requires_context", {}))
        out[name] = found
    return out


def test_every_sentence_intent_has_a_script():
    scripts, slots = _scripts(), _slots()
    assert set(slots) <= set(scripts)


def test_scripts_with_untoolable_slots_are_voice_only():
    scripts, slots = _scripts(), _slots()
    exposed = []
    for name, script in scripts.items():
        extra = slots.get(name, set()) - TOOL_SLOTS
        if extra and script.get("platforms") != ["conversation"]:
            exposed.append(f"{name}: {sorted(extra)}")
    assert not exposed, "add `platforms: [conversation]`:\n  " + "\n  ".join(exposed)


def test_slotless_scripts_stay_tools():
    # A call with no arguments is right for these, so the LLM may keep them.
    scripts, slots = _scripts(), _slots()
    hidden = [n for n, s in scripts.items() if s.get("platforms") and not slots.get(n, set()) - TOOL_SLOTS]
    assert not hidden, f"needlessly hidden from the LLM: {hidden}"
