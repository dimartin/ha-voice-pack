"""The LLM-facing scripts build a sentence and hand it to the built-in agent. Each
sentence must match the intended intent with the right slots, and the time must
parse, or the script answers something other than what the model asked for."""
import re
from datetime import timedelta

import pytest
import yaml
from hassil import recognize_best
from jinja2 import Environment

from conftest import NOW, ROOT

ENV = Environment()
ENV.filters["regex_replace"] = lambda v, find="", replace="", ignorecase=False: re.sub(
    find, replace, v, flags=re.I if ignorecase else 0)
ENV.tests["match"] = lambda v, find="": re.match(find, v) is not None


def script(package, name):
    return yaml.safe_load((ROOT / "packages" / package).read_text())["script"][name]


def render(template, **fields):
    return ENV.from_string(template).render(**fields).strip()


def weather_text(**fields):
    s = script("voice_weather.yaml", "weather_forecast")["sequence"]
    d = render(s[0]["variables"]["d"], **fields)
    return render(s[1]["data"]["text"], d=d, **fields)


def reminder_text(**fields):
    return render(script("voice_reminders.yaml", "set_reminder")["sequence"][0]["variables"]["text"], **fields)


@pytest.mark.parametrize("fields, intent, day", [
    ({"day": "today"}, "WeatherForecast", "today"),
    ({"day": "tomorrow"}, "WeatherForecast", "tomorrow"),
    ({"day": "tonight"}, "WeatherForecast", "tonight"),
    ({"day": "tomorrow", "rain": True}, "RainCheck", "tomorrow"),
    ({"day": "tonight", "rain": True}, "RainCheck", "tonight"),
    ({"day": "next week"}, "WeatherForecast", "today"),  # an unknown day falls back to today
])
def test_weather_script_sentences(intents, fields, intent, day):
    text = weather_text(**fields)
    result = recognize_best(text, intents, language="en")
    assert result is not None, text
    assert result.intent.name == intent and result.entities["day"].value == day, text


@pytest.mark.parametrize("fields, task, clock, days", [
    ({"task": "call the bank", "time": "3 pm"}, "call the bank", "15:00", 0),
    ({"task": "call the bank", "time": "3"}, "call the bank", "15:00", 0),
    ({"task": "to take my 2 pills", "time": "7:30 pm"}, "take my 2 pills", "19:30", 0),
    ({"task": "move the car at the station", "time": "5 pm"}, "move the car at the station", "17:00", 0),
    ({"task": "call mom", "time": "tomorrow at 9"}, "call mom", "09:00", 1),
    ({"task": "call mom", "time": "9 am tomorrow"}, "call mom", "09:00", 1),
])
def test_reminder_script_at_a_time(intents, vp_reminder, fields, task, clock, days):
    text = reminder_text(**fields)
    result = recognize_best(text, intents, language="en")
    assert result is not None and result.intent.name == "RemindAt", text
    e = {k: v.value for k, v in result.entities.items()}
    parsed = vp_reminder(e["time"].strip(), e.get("task", "").strip(), e.get("day", ""))
    assert parsed["ok"], (text, parsed)
    assert parsed["task"] == task, text
    assert parsed["local"][11:16] == clock, (text, parsed)
    assert parsed["local"][:10] == (NOW + timedelta(days=days)).strftime("%Y-%m-%d"), (text, parsed)


@pytest.mark.parametrize("minutes", [1, 20, 120, 720])
def test_reminder_script_after_a_delay(intents, minutes):
    text = reminder_text(task="check the oven", minutes=minutes, time="")
    result = recognize_best(text, intents, language="en")
    assert result is not None and result.intent.name == "RemindIn", text
    assert result.entities["minutes"].value == minutes
    assert result.entities["task"].value.strip() == "check the oven"


def test_scripts_are_offered_to_the_llm():
    # These are the LLM's way in, so they must not be voice-only like the intent scripts.
    for package, name in [("voice_weather.yaml", "weather_forecast"), ("voice_reminders.yaml", "set_reminder")]:
        s = script(package, name)
        assert s.get("description") and s.get("fields"), name
        assert "platforms" not in s, name


def test_reminder_task_that_starts_with_about(intents, vp_reminder):
    text = reminder_text(task="about the meeting", time="3 pm")
    assert text == "remind me at 3 pm about the meeting"
    result = recognize_best(text, intents, language="en")
    assert result.intent.name == "RemindAt" and result.entities["task"].value.strip() == "the meeting"


def pick(query, found):
    s = script("voice_music.yaml", "voice_pack_play_search")["sequence"]
    q = render(s[0]["variables"]["q"], query=query)
    return eval(render(s[3]["variables"]["pick"], q=q, query=query, found=found) or "{}")


BEATLES = {"artists": [{"name": "The Beatles", "uri": "library://artist/1", "media_type": "artist"}],
           "albums": [{"name": "Abbey Road", "uri": "library://album/2", "media_type": "album"}],
           "playlists": [], "tracks": [{"name": "Let It Be", "uri": "library://track/3", "media_type": "track"}]}


@pytest.mark.parametrize("query", ["the Beatles", "The Beatles", "Beatles", "some Beatles"])
def test_exact_name_with_an_article_plays_the_artist(query):
    # "Beatles" alone is not an exact match, so it falls back to the first track.
    want = "library://track/3" if query in ("Beatles", "some Beatles") else "library://artist/1"
    assert pick(query, BEATLES)["uri"] == want, query


def test_no_result_picks_nothing():
    assert pick("nothing", {"artists": [], "albums": [], "playlists": [], "tracks": []}) == {}
