"""vp_when and vp_roll in custom_templates/voice_pack.jinja (fixtures in conftest.py)."""

import pytest


@pytest.mark.parametrize(
    "text, day, local, say",
    [
        # digits, with and without the colon speech-to-text drops
        ("935 AM", "", "2026-10-13 09:35:00", "9:35 AM tomorrow"),
        ("9:35 pm", "", "2026-10-12 21:35:00", "9:35 PM"),
        ("1.15 a.m.", "", "2026-10-13 01:15:00", "1:15 AM tomorrow"),
        ("19:00", "", "2026-10-12 19:00:00", "7:00 PM"),
        ("1230", "", "2026-10-13 00:30:00", "12:30 AM tomorrow"),
        # no am/pm: whichever comes next
        ("7", "", "2026-10-12 19:00:00", "7:00 PM"),
        ("2", "", "2026-10-12 14:00:00", "2:00 PM"),
        ("1:15", "", "2026-10-13 01:15:00", "1:15 AM tomorrow"),
        # number words
        ("one fifteen p.m.", "", "2026-10-13 13:15:00", "1:15 PM tomorrow"),
        ("one thirty pm", "", "2026-10-12 13:30:00", "1:30 PM"),
        ("seven oh five am", "", "2026-10-13 07:05:00", "7:05 AM tomorrow"),
        ("twelve forty five pm", "", "2026-10-13 12:45:00", "12:45 PM tomorrow"),
        ("six o'clock", "", "2026-10-12 18:00:00", "6:00 PM"),
        ("nine", "", "2026-10-12 21:00:00", "9:00 PM"),
        ("noon", "", "2026-10-13 12:00:00", "12:00 PM tomorrow"),
        ("midnight", "", "2026-10-13 00:00:00", "12:00 AM tomorrow"),
        # tomorrow
        ("9", "tomorrow", "2026-10-13 09:00:00", "9:00 AM tomorrow"),
        ("3 pm tomorrow", "", "2026-10-13 15:00:00", "3:00 PM tomorrow"),
        # past / to
        ("quarter past six", "", "2026-10-12 18:15:00", "6:15 PM"),
        ("a quarter past six", "", "2026-10-12 18:15:00", "6:15 PM"),
        ("half past seven", "", "2026-10-12 19:30:00", "7:30 PM"),
        ("quarter to eight", "", "2026-10-12 19:45:00", "7:45 PM"),
        ("ten to nine", "", "2026-10-12 20:50:00", "8:50 PM"),
        ("twenty five past 4", "", "2026-10-12 16:25:00", "4:25 PM"),
        ("five past ten pm", "", "2026-10-12 22:05:00", "10:05 PM"),
        ("ten to one", "", "2026-10-13 00:50:00", "12:50 AM tomorrow"),
        ("at quarter to eight tomorrow", "", "2026-10-13 07:45:00", "7:45 AM tomorrow"),
        # part of day, spaced meridiem, "please" from the end of a sentence
        ("7 in the evening", "", "2026-10-12 19:00:00", "7:00 PM"),
        ("6 in the morning", "", "2026-10-13 06:00:00", "6:00 AM tomorrow"),
        ("9 tonight", "", "2026-10-12 21:00:00", "9:00 PM"),
        ("5 p m", "", "2026-10-12 17:00:00", "5:00 PM"),
        ("5 pm please", "", "2026-10-12 17:00:00", "5:00 PM"),
        # review of PR 3: hyphens, part of day after "tomorrow", twelve, "at half", noon digits, "half six"
        ("twenty-five past four", "", "2026-10-12 16:25:00", "4:25 PM"),
        ("twenty-five to five", "", "2026-10-12 16:35:00", "4:35 PM"),
        ("7 tomorrow evening", "", "2026-10-13 19:00:00", "7:00 PM tomorrow"),
        ("7 tomorrow night", "", "2026-10-13 19:00:00", "7:00 PM tomorrow"),
        ("tomorrow evening at 7", "", "2026-10-13 19:00:00", "7:00 PM tomorrow"),
        ("ten to twelve am", "", "2026-10-12 23:50:00", "11:50 PM"),
        ("ten to twelve pm", "", "2026-10-13 11:50:00", "11:50 AM tomorrow"),
        ("at half past seven", "", "2026-10-12 19:30:00", "7:30 PM"),
        ("12 noon", "", "2026-10-13 12:00:00", "12:00 PM tomorrow"),
        ("half six", "", "2026-10-12 18:30:00", "6:30 PM"),
        # round 2: a part of day is not a spoken am/pm for "to twelve"; twelve at night is midnight
        ("ten to twelve tonight", "", "2026-10-12 23:50:00", "11:50 PM"),
        ("quarter to twelve at night", "", "2026-10-12 23:45:00", "11:45 PM"),
        ("ten to twelve in the morning", "", "2026-10-13 11:50:00", "11:50 AM tomorrow"),
        ("ten to twelve noon", "", "2026-10-13 11:50:00", "11:50 AM tomorrow"),
        ("ten to twelve midnight", "", "2026-10-12 23:50:00", "11:50 PM"),
        ("12 tonight", "", "2026-10-13 00:00:00", "12:00 AM tomorrow"),
        ("12 tomorrow night", "", "2026-10-14 00:00:00", "12:00 AM on Wednesday"),
        ("12 in the afternoon", "", "2026-10-13 12:00:00", "12:00 PM tomorrow"),
    ],
)
def test_parses(vp_when, text, day, local, say):
    got = vp_when(text, day)
    assert got["ok"], got
    assert (got["local"], got["say"]) == (local, say)


@pytest.mark.parametrize(
    "text",
    [
        "banana", "25:00", "13 pm", "9:75", "",
        # words that aren't a time: the wildcard took part of the task
        "the station at 5 pm", "5 pm to call mom",
        "fifteen to thirteen", "a few minutes",
        # a part-of-day word the part-of-day pattern did not read
        "7 evening", "night 7",
    ],
)
def test_rejects(vp_when, text):
    assert vp_when(text)["ok"] is False


@pytest.mark.parametrize(
    "time, task, local, kept",
    [
        ("5 pm", "call mom", "2026-10-12 17:00:00", "call mom"),
        # the matcher cut at the first "to": the hour goes back to the time
        ("ten", "nine to call mom", "2026-10-12 20:50:00", "call mom"),
        ("quarter", "eight to take my 2 pills", "2026-10-12 19:45:00", "take my 2 pills"),
        ("20", "9 pm to stretch", "2026-10-12 20:40:00", "stretch"),
        ("ten", "twelve tonight to call mom", "2026-10-12 23:50:00", "call mom"),
        ("ten", "twelve noon to call mom", "2026-10-13 11:50:00", "call mom"),
        ("ten", "twelve midnight to call mom", "2026-10-12 23:50:00", "call mom"),
        ("quarter", "eight in the morning to stretch", "2026-10-13 07:45:00", "stretch"),
        # the matcher cut at the first "at": the place goes back to the task
        ("the station at 5 pm", "move the car", "2026-10-12 17:00:00", "move the car at the station"),
        # day words at the end of the task belong to the time
        ("7", "call mom tomorrow evening", "2026-10-13 19:00:00", "call mom"),
        # the minutes word must look like minutes: "10 to one", but not "7 to one"
        ("7", "one to one with sam", "2026-10-12 19:00:00", "one to one with sam"),
        # left alone: "nine to five" is a task here, the time is complete
        ("7 pm", "nine to five shift notes", "2026-10-12 19:00:00", "nine to five shift notes"),
    ],
)
def test_reminder_repairs_bad_splits(vp_reminder, time, task, local, kept):
    got = vp_reminder(time, task)
    assert got["ok"], got
    assert (got["local"], got["task"]) == (local, kept)


def test_reminder_reads_part_of_day_from_the_day_slot(vp_reminder):
    got = vp_reminder("7", "call mom", "tomorrow evening")
    assert (got["ok"], got["local"]) == (True, "2026-10-13 19:00:00")


def test_reminder_refuses_unreadable_time(vp_reminder):
    got = vp_reminder("the station", "move the car")
    assert got["ok"] is False
    assert got["task"] == "move the car"


@pytest.mark.parametrize(
    "start, repeat, step, local",
    [
        # setting an alarm: keep the day if it qualifies, else roll forward
        ("2026-10-13 07:00", "weekdays", False, "2026-10-13 07:00:00"),
        ("2026-10-17 07:00", "weekdays", False, "2026-10-19 07:00:00"),  # Sat -> Mon
        ("2026-10-13 07:00", "weekends", False, "2026-10-17 07:00:00"),  # Tue -> Sat
        ("2026-10-13 07:00", "once", False, "2026-10-13 07:00:00"),
        # after a ring: next qualifying day
        ("2026-10-12 07:00", "daily", True, "2026-10-13 07:00:00"),
        ("2026-10-16 07:00", "weekdays", True, "2026-10-19 07:00:00"),  # Fri -> Mon
        ("2026-10-17 08:30", "weekends", True, "2026-10-18 08:30:00"),  # Sat -> Sun
        ("2026-10-18 08:30", "weekends", True, "2026-10-24 08:30:00"),  # Sun -> Sat
        # DST ends 2026-11-01 in New York: wall-clock time stays 7:00
        ("2026-10-31 07:00", "daily", True, "2026-11-01 07:00:00"),
    ],
)
def test_roll(vp_roll, start, repeat, step, local):
    assert vp_roll(start, repeat, step)["local"] == local


@pytest.mark.parametrize(
    "text, local",
    [
        ("7", "2026-10-13 07:00:00"),  # afternoon now, but an alarm at 7 means morning
        ("6:30", "2026-10-13 06:30:00"),
        ("11", "2026-10-13 11:00:00"),
        ("3", "2026-10-12 15:00:00"),  # outside 4-11: next occurrence, 3 PM today
        ("7 pm", "2026-10-12 19:00:00"),
    ],
)
def test_alarm_prefers_morning(vp_when, text, local):
    assert vp_when(text, prefer="morning")["local"] == local
