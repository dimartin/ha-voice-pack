"""Shared fixtures: the pack's sentences as Home Assistant merges them, and the
voice_pack.jinja macros rendered with plain Jinja2 against a fixed clock.

Home Assistant's template helpers that the macros use (now, today_at, timedelta,
regex_findall, to_json, from_json, as_datetime, as_local, the search test) are stubbed with
a fixed clock: Monday 2026-10-12 13:20 in America/New_York.
"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml
from hassil import Intents
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent.parent
SENTENCES = ROOT / "custom_sentences" / "en"
TZ = ZoneInfo("America/New_York")
NOW = datetime(2026, 10, 12, 13, 20, tzinfo=TZ)


def sentence_files():
    return {p.name: yaml.safe_load(p.read_text()) for p in sorted(SENTENCES.glob("*.yaml"))}


@pytest.fixture(scope="session")
def intents():
    merged = {"language": "en", "intents": {}, "lists": {}}
    for data in sentence_files().values():
        merged["intents"].update(data.get("intents", {}))
        merged["lists"].update(data.get("lists", {}))
    # Built into Home Assistant, used by media.yaml.
    merged["lists"].setdefault("search_query", {"wildcard": True})
    # Home Assistant fills {area} from the home's areas; these stand in for them.
    merged["lists"].setdefault("area", {"values": ["Kitchen", "Den", "Dining Room", "Office"]})
    return Intents.from_dict(merged)


@pytest.fixture(scope="session")
def module():
    env = Environment(loader=FileSystemLoader(ROOT / "custom_templates"))
    env.globals.update(
        now=lambda: NOW,
        today_at=lambda hm: datetime.combine(NOW.date(), datetime.strptime(hm, "%H:%M").time(), TZ),
        timedelta=timedelta,
    )
    env.filters.update(
        regex_findall=lambda value, find="": re.findall(find, value),
        to_json=json.dumps,
        from_json=json.loads,
        as_datetime=lambda ts: datetime.fromtimestamp(float(ts), timezone.utc),
        as_local=lambda dt: dt.astimezone(TZ),
    )
    env.tests["search"] = lambda value, find="": re.search(find, value) is not None
    return env.get_template("voice_pack.jinja").module


@pytest.fixture(scope="session")
def vp_when(module):
    return lambda text, day="", prefer="": json.loads(str(module.vp_when(text, day, prefer)))


@pytest.fixture(scope="session")
def vp_reminder(module):
    return lambda time, task, day="": json.loads(str(module.vp_reminder(time, task, day)))


@pytest.fixture(scope="session")
def vp_roll(module):
    return lambda local, repeat, step: json.loads(
        str(module.vp_roll(datetime.strptime(local, "%Y-%m-%d %H:%M").replace(tzinfo=TZ).timestamp(), repeat, step))
    )
