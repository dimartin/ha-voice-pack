"""Sentence matching for custom_sentences/en, using hassil (Home Assistant's matcher).

Checks which intent and slots each phrasing produces. Rendering the intent
scripts needs a running Home Assistant; see README "Checking a live install".
"""

from hassil import recognize_best
import pytest

from conftest import sentence_files


def test_shared_lists_are_identical():
    # Home Assistant merges every file into one namespace, so a list defined
    # twice with different values silently replaces the other file's list.
    seen = {}
    for name, data in sentence_files().items():
        for list_name, definition in data.get("lists", {}).items():
            if list_name in seen:
                other, other_def = seen[list_name]
                assert definition == other_def, f"list {list_name!r} differs in {name} and {other}"
            seen[list_name] = (name, definition)


def _match(intents, text):
    # Home Assistant's default agent uses recognize_best (most literal text wins).
    result = recognize_best(text, intents, language="en")
    assert result is not None, f"no match: {text!r}"
    return result.intent.name, {k: v.value for k, v in result.entities.items()}


def _slot(value):
    return value.strip() if isinstance(value, str) else value


@pytest.mark.parametrize(
    "text, intent, slots",
    [
        # alarm
        ("can you set a 935 AM alarm", "SetAlarm", {"time": "935 AM"}),
        ("set an alarm for 6:15", "SetAlarm", {"time": "6:15"}),
        ("wake me up at 7", "SetAlarm", {"time": "7"}),
        ("cancel my alarm", "CancelAlarm", {}),
        ("when is my alarm", "AlarmStatus", {}),
        ("set an alarm for one fifteen pm", "SetAlarm", {"time": "one fifteen pm"}),
        ("set an alarm for 6:30 with chimes", "SetAlarm", {"time": "6:30", "alarm_sound": "chimes"}),
        ("wake me up at 7 using the gentle sound", "SetAlarm", {"time": "7", "alarm_sound": "gentle"}),
        ("set a 7 am pulse alarm", "SetAlarm", {"time": "7 am", "alarm_sound": "pulse"}),
        ("delete that alarm", "CancelAlarm", {}),
        ("change my alarm sound to beeps", "SetAlarmSound", {"alarm_sound": "classic"}),
        ("set an alarm for 7 am on weekdays", "SetAlarm", {"time": "7 am", "alarm_repeat": "weekdays"}),
        ("set an alarm for 6:30 every day with chimes", "SetAlarm", {"time": "6:30", "alarm_repeat": "daily", "alarm_sound": "chimes"}),
        ("set a weekday alarm for 6:45", "SetAlarm", {"alarm_repeat": "weekdays", "time": "6:45"}),
        ("set a weekend alarm for 9 with chimes", "SetAlarm", {"alarm_repeat": "weekends", "time": "9", "alarm_sound": "chimes"}),
        ("wake me up at 9 on weekends", "SetAlarm", {"time": "9", "alarm_repeat": "weekends"}),
        ("stop the alarm", "DismissAlarm", {}),
        ("dismiss", "DismissAlarm", {}),
        ("I'm up", "DismissAlarm", {}),
        ("turn off my alarm", "CancelAlarm", {}),
        ("snooze", "SnoozeAlarm", {}),
        ("snooze for 10 minutes", "SnoozeAlarm", {"snooze_minutes": 10}),
        ("snooze the alarm for five minutes", "SnoozeAlarm", {"snooze_minutes": 5}),
        ("skip tomorrow's alarm", "SkipAlarm", {}),
        ("don't wake me up tomorrow", "SkipAlarm", {}),
        ("when is my next alarm", "AlarmStatus", {}),
        ("use the chime sound for my alarm", "SetAlarmSound", {"alarm_sound": "chimes"}),
        ("what alarm sounds are there", "AlarmSoundStatus", {}),
        ("what's my alarm sound", "AlarmSoundStatus", {}),
        ("play the pulse alarm", "PreviewAlarmSound", {"alarm_sound": "pulse"}),
        ("what does the gentle alarm sound like", "PreviewAlarmSound", {"alarm_sound": "gentle"}),
        # weather
        ("what's the weather this evening", "WeatherForecast", {"day": "tonight"}),
        ("what's the weather tomorrow", "WeatherForecast", {"day": "tomorrow"}),
        ("will it rain tonight", "RainCheck", {"day": "tonight"}),
        ("do I need an umbrella", "RainCheck", {}),
        # reminders, clock time
        ("remind me to call mom at 5 pm", "RemindAt", {"task": "call mom", "time": "5 pm"}),
        ("remind me at 7:30 to take out the trash", "RemindAt", {"time": "7:30", "task": "take out the trash"}),
        ("remind me tomorrow at 9 to call the dentist", "RemindAt", {"day": "tomorrow", "time": "9", "task": "call the dentist"}),
        ("remind me to water the plants tomorrow at 8 am", "RemindAt", {"task": "water the plants", "day": "tomorrow", "time": "8 am"}),
        ("set a reminder for 3 pm to move the car", "RemindAt", {"time": "3 pm", "task": "move the car"}),
        # reminders, relative
        ("remind me in 10 minutes to check the oven", "RemindIn", {"minutes": 10, "task": "check the oven"}),
        ("remind me in five minutes to check the oven", "RemindIn", {"minutes": 5, "task": "check the oven"}),
        ("remind me to switch the laundry in 45 minutes", "RemindIn", {"task": "switch the laundry", "minutes": 45}),
        ("remind me in two hours to feed the dog", "RemindIn", {"hours": 2, "task": "feed the dog"}),
        ("remind me in an hour to call back", "RemindIn", {"hours": 1, "task": "call back"}),
        ("remind me to stretch in half an hour", "RemindIn", {"task": "stretch", "minutes": 30}),
        ("remind me about the meeting in 2 hours", "RemindIn", {"verb": "about", "task": "the meeting", "hours": 2}),
        ("remind me about the dentist at 1:30 PM", "RemindAt", {"verb": "about", "task": "the dentist", "time": "1:30 PM"}),
        ("remind me at noon about lunch", "RemindAt", {"verb": "about", "time": "noon", "task": "lunch"}),
        ("can you remind me to call mom at 5 pm", "RemindAt", {"task": "call mom", "time": "5 pm"}),
        ("please remind me in 10 minutes to check the oven", "RemindIn", {"minutes": 10, "task": "check the oven"}),
        ("set a reminder to move the car at 3 pm", "RemindAt", {"task": "move the car", "time": "3 pm"}),
        ("remind me to stretch in half an hour please", "RemindIn", {"task": "stretch", "minutes": 30}),
        # reminders, manage
        ("what are my reminders", "ListReminders", {}),
        ("do I have any reminders", "ListReminders", {}),
        ("cancel all my reminders", "CancelReminders", {}),
        ("cancel the reminder to call mom", "CancelReminder", {"task": "call mom"}),
    ],
)
def test_sentence(intents, text, intent, slots):
    got_intent, got_slots = _match(intents, text)
    assert got_intent == intent
    assert {k: _slot(v) for k, v in got_slots.items()} == slots


@pytest.mark.parametrize("text", ["set a timer for 5 minutes", "turn on the kitchen light", "stop", "pause"])
def test_leaves_builtin_phrasings_alone(intents, text):
    assert recognize_best(text, intents, language="en") is None


@pytest.mark.parametrize(
    "text, query",
    [
        ("could you play some dance music", "some dance music"),
        ("can you please play Nina Simone", "Nina Simone"),
        ("put on some jazz", "some jazz"),
        ("I want to hear Steely Dan", "Steely Dan"),
        ("let's listen to the Beatles", "the Beatles"),
        ("can you play music by the band Tool", "Tool"),
        ("play music by Tool", "Tool"),
        ("play some songs by the artist Nina Simone", "Nina Simone"),
        ("play something by Steely Dan please", "Steely Dan"),
    ],
)
def test_media_phrasings_play_in_the_satellite_area(intents, text, query):
    # The area slot comes from the satellite's context, so PlayMedia plays on that
    # area's player instead of whatever the LLM would pick.
    result = recognize_best(text, intents, language="en", intent_context={"area": "Den"})
    assert result is not None, f"no match: {text!r}"
    assert result.intent.name == "PlayMedia"
    assert result.entities["search_query"].value.strip() == query
    assert result.entities["area"].value == "Den"


@pytest.mark.parametrize("text, intent", [
    ("play rock", "PlayGenre"),
    ("could you play some rock music", "PlayGenre"),
    ("play Nina Simone", "PlayMedia"),
    ("play the pulse alarm", "PreviewAlarmSound"),
])
def test_free_text_play_does_not_take_genres_or_alarm_sounds(text, intent):
    # "play {search_query}" is a wildcard; a genre or alarm-sound sentence must still win.
    import sys

    from hassil import Intents

    from conftest import ROOT, sentence_files
    sys.path.insert(0, str(ROOT / "tools"))
    from ma_genre_sentences import build

    merged = {"language": "en", "intents": {}, "lists": {"search_query": {"wildcard": True}}}
    files = list(sentence_files().values()) + [build([{"id": 1, "name": "Rock", "tracks": 9}], min_tracks=1)[0]]
    for data in files:
        merged["intents"].update(data.get("intents", {}))
        merged["lists"].update(data.get("lists", {}))
    result = recognize_best(text, Intents.from_dict(merged), language="en", intent_context={"area": "Den"})
    assert result is not None and result.intent.name == intent, (text, result and result.intent.name)


@pytest.mark.parametrize("text, intent, slots", [
    ("play jazz in the kitchen", "PlayGenre", {"genre": "Jazz", "area": "Kitchen"}),
    ("could you put on some rock music in the dining room", "PlayGenre", {"genre": "Rock", "area": "Dining Room"}),
    ("play Nina Simone on the kitchen speaker", "PlayMedia", {"search_query": "Nina Simone", "area": "Kitchen"}),
    ("could you play the Beatles in the office please", "PlayMedia", {"search_query": "the Beatles", "area": "Office"}),
    ("play Nina Simone", "PlayMedia", {"search_query": "Nina Simone", "area": "Den"}),
    # every phrasing has a room form
    ("let's hear jazz in the kitchen", "PlayGenre", {"genre": "Jazz", "area": "Kitchen"}),
    ("I'd like to hear jazz", "PlayGenre", {"genre": "Jazz", "area": "Den"}),
    ("I'd like to hear jazz in the kitchen", "PlayGenre", {"genre": "Jazz", "area": "Kitchen"}),
    ("I'd like to hear Nina Simone", "PlayMedia", {"search_query": "Nina Simone", "area": "Den"}),
    ("I'd like to listen to Nina Simone in the kitchen", "PlayMedia", {"search_query": "Nina Simone", "area": "Kitchen"}),
    ("I want to listen to some rock music in the office", "PlayGenre", {"genre": "Rock", "area": "Office"}),
    ("I want to hear Nina Simone in the kitchen", "PlayMedia", {"search_query": "Nina Simone", "area": "Kitchen"}),
    ("let's listen to the Beatles on the dining room speaker", "PlayMedia", {"search_query": "the Beatles", "area": "Dining Room"}),
    ("play music by the band Tool in the kitchen", "PlayMedia", {"search_query": "Tool", "area": "Kitchen"}),
    ("can you play songs by Tool on the kitchen speaker", "PlayMedia", {"search_query": "Tool", "area": "Kitchen"}),
    # an unknown room is part of the search, in the satellite's area
    ("play jazz in the garage", "PlayMedia", {"search_query": "jazz in the garage", "area": "Den"}),
])
def test_a_named_room_beats_the_satellites(text, intent, slots):
    import sys

    from hassil import Intents

    from conftest import ROOT, sentence_files
    sys.path.insert(0, str(ROOT / "tools"))
    from ma_genre_sentences import build

    merged = {"language": "en", "intents": {}, "lists": {"search_query": {"wildcard": True},
              "area": {"values": ["Kitchen", "Den", "Dining Room", "Office"]}}}
    genres = build([{"id": 1, "name": "Rock", "tracks": 9}, {"id": 2, "name": "Jazz", "tracks": 9}], min_tracks=1)[0]
    for data in list(sentence_files().values()) + [genres]:
        merged["intents"].update(data.get("intents", {}))
        merged["lists"].update(data.get("lists", {}))
    result = recognize_best(text, Intents.from_dict(merged), language="en", intent_context={"area": "Den"})
    assert result is not None and result.intent.name == intent, (text, result and result.intent.name)
    got = {k: (v.value.strip() if isinstance(v.value, str) else v.value) for k, v in result.entities.items()}
    assert got == slots, text
