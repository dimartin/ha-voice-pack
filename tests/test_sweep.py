"""Sweep generated phrasings through hassil and vp_when, the way Home Assistant does.

Hand-picked tests in test_sentences.py prove that the sentences we thought of
work. This sweep generates about 2,600 more (openers x times x tasks) and
sorts every one into one of three outcomes:

  SUSPECT  it matched, but something landed in the wrong place: the wrong
           intent, a time inside the reminder text, reminder text inside
           {time}, or a time that vp_when reads as a different clock time.
           Home Assistant then sets a reminder or alarm at the wrong time and
           confirms it as a success. This is the worst failure the pack has,
           so every SUSPECT fails the test.

  MISS     nothing matched (the request falls through to the LLM, or errors),
           or it matched but vp_when found no time ("Sorry, I didn't catch
           when"). Both are loud, so a miss is not automatically a bug: some
           generated sentences should be refused. Each one needs a verdict in
           sweep_verdicts.yaml, "refuse" or "gap" (should work, doesn't yet).
           An unpinned miss fails, so a new one can't slip in unnoticed; a
           pinned one that now matches fails too, so the file stays current.

  OK       intent, slots and parsed time are all as generated.

The clock is the one in conftest.py: Monday 2026-10-12 13:20, New York.

Run `pytest tests/test_sweep.py -s` to print the report.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml
from hassil import recognize_best

from conftest import NOW

VERDICTS = Path(__file__).with_name("sweep_verdicts.yaml")


@dataclass
class Case:
    text: str
    intent: str
    slots: dict = field(default_factory=dict)  # expected slot values; "time" is checked by clock instead
    clock: str | None = None  # expected "HH:MM" that vp_when should produce from the {time} slot
    day: str = ""
    prefer: str = ""
    days: int | None = None  # expected date offset from today; None: any time in the next 24 hours


# (spoken, HH:MM for a reminder said at 13:20, HH:MM for an alarm). A reminder
# with no am/pm takes the next occurrence; an alarm reads a bare 4-11 as morning.
TIMES = [
    ("5 pm", "17:00", "17:00"),
    ("5 p.m.", "17:00", "17:00"),
    ("5pm", "17:00", "17:00"),
    ("5:30 pm", "17:30", "17:30"),
    ("5:30pm", "17:30", "17:30"),
    ("5 30 pm", "17:30", "17:30"),
    ("530 pm", "17:30", "17:30"),
    ("5.30 p.m.", "17:30", "17:30"),
    ("9:35 am", "09:35", "09:35"),
    ("935 AM", "09:35", "09:35"),
    ("9.35 a.m.", "09:35", "09:35"),
    ("7", "19:00", "07:00"),
    ("6:45", "18:45", "06:45"),
    ("19:00", "19:00", "19:00"),
    ("seven oh five am", "07:05", "07:05"),
    ("one fifteen pm", "13:15", "13:15"),
    ("six thirty", "18:30", "06:30"),
    ("6 o'clock", "18:00", "06:00"),
    ("noon", "12:00", "12:00"),
    ("midnight", "00:00", "00:00"),
    ("quarter past six", "18:15", "06:15"),
    ("half past seven", "19:30", "07:30"),
    ("quarter to eight", "19:45", "07:45"),
    ("ten to nine", "20:50", "08:50"),
    ("five past ten pm", "22:05", "22:05"),
    ("twenty-five past four", "16:25", "04:25"),
    ("twenty-five to five", "16:35", "04:35"),
    ("ten to twelve am", "23:50", "23:50"),
    ("ten to twelve pm", "11:50", "11:50"),
    ("12 noon", "12:00", "12:00"),
    ("half six", "18:30", "06:30"),
    ("7 in the evening", "19:00", "19:00"),
    ("ten to twelve tonight", "23:50", "23:50"),
    ("ten to twelve in the morning", "11:50", "11:50"),
    ("ten to twelve noon", "11:50", "11:50"),
    ("ten to twelve midnight", "23:50", "23:50"),
]

# Day words that land inside the {time} or {task} wildcard, and other one-offs.
EXTRA = [
    Case("remind me to call mom at 7 tomorrow evening", "RemindAt", {"task": "call mom"}, "19:00", days=1),
    Case("remind me to call mom at 7 tomorrow night", "RemindAt", {"task": "call mom"}, "19:00", days=1),
    Case("remind me to call mom tomorrow evening at 7", "RemindAt", {"task": "call mom", "day": "tomorrow evening"}, "19:00", days=1),
    Case("remind me to call mom tomorrow morning at 7", "RemindAt", {"task": "call mom", "day": "tomorrow morning"}, "07:00", days=1),
    Case("remind me to call mom at 6 this evening", "RemindAt", {"task": "call mom"}, "18:00", days=0),
    Case("remind me tomorrow evening at 7 to call mom", "RemindAt", {"task": "call mom", "day": "tomorrow evening"}, "19:00", days=1),
    Case("wake me up at 7 tomorrow evening", "SetAlarm", {}, "19:00", prefer="morning", days=1),
    Case("set an alarm for tomorrow at half past seven", "SetAlarm", {}, "07:30", prefer="morning", days=1),
    Case("set an alarm for seven thirty tomorrow morning", "SetAlarm", {}, "07:30", prefer="morning", days=1),
    Case("remind me tonight at ten to twelve to call mom", "RemindAt", {"task": "call mom", "day": "tonight"}, "23:50", days=0),
]

# Tasks people say, including ones with numbers and "at" in them.
TASKS = [
    "call mom",
    "take out the trash",
    "take my 2 pills",
    "move the car at the station",
    "call the 9 o'clock meeting",
    "check on the kids",
]

REMIND_AT = [
    ("remind me to {task} at {time}", ""),
    ("remind me at {time} to {task}", ""),
    ("remind me to {task} tomorrow at {time}", "tomorrow"),
    ("remind me tomorrow at {time} to {task}", "tomorrow"),
    ("set a reminder for {time} to {task}", ""),
    ("set a reminder at {time} to {task}", ""),
    # phrasings the sentences don't have yet
    ("can you remind me to {task} at {time}", ""),
    ("please remind me to {task} at {time}", ""),
    ("set a reminder to {task} at {time}", ""),
    ("remind me to {task} at {time} please", ""),
]

REMIND_ABOUT = [
    ("remind me about {task} at {time}", ""),
    ("remind me at {time} about {task}", ""),
]

# (spoken, slot, value)
DURATIONS = [
    ("5 minutes", "minutes", 5),
    ("five minutes", "minutes", 5),
    ("1 minute", "minutes", 1),
    ("45 minutes", "minutes", 45),
    ("2 hours", "hours", 2),
    ("two hours", "hours", 2),
    ("an hour", "hours", 1),
    ("half an hour", "minutes", 30),
    ("ninety minutes", "minutes", 90),
    ("a few minutes", None, None),
]

REMIND_IN = [
    "remind me in {dur} to {task}",
    "remind me to {task} in {dur}",
    "can you remind me in {dur} to {task}",
]

ALARM = [
    ("set an alarm for {time}", {}),
    ("set an alarm at {time}", {}),
    ("wake me up at {time}", {}),
    ("set a {time} alarm", {}),
    ("could you set an alarm for {time} please", {}),
    ("set an alarm for {time} on weekdays", {"alarm_repeat": "weekdays"}),
    ("set an alarm for {time} with chimes", {"alarm_sound": "chimes"}),
    ("wake me up at {time} every day", {"alarm_repeat": "daily"}),
]


def cases():
    out = []
    for template, day in REMIND_AT:
        for spoken, clock, morning in TIMES:
            for task in TASKS:
                slots = {"task": task, **({"day": day} if day else {})}
                # "tomorrow at 7" is the earliest 7 tomorrow, as for an alarm
                out.append(Case(template.format(task=task, time=spoken), "RemindAt", slots, morning if day else clock, day,
                                days=1 if day else None))
    for template, day in REMIND_ABOUT:
        for spoken, clock, _ in TIMES[::3]:
            for task in ("the meeting", "the 2 pm call"):
                out.append(Case(template.format(task=task, time=spoken), "RemindAt", {"task": task, "verb": "about"}, clock))
    for template in REMIND_IN:
        for spoken, slot, value in DURATIONS:
            for task in TASKS[:3]:
                slots = {"task": task, **({slot: value} if slot else {})}
                out.append(Case(template.format(task=task, dur=spoken), "RemindIn", slots))
    for template, slots in ALARM:
        for spoken, _, clock in TIMES:
            out.append(Case(template.format(time=spoken), "SetAlarm", slots, clock, prefer="morning"))
    return out + EXTRA


def _value(v):
    return v.strip() if isinstance(v, str) else v


def judge(case, intents, vp_when, vp_reminder):
    """Return ("ok" | "miss" | "suspect", reason), judging what the intent scripts would do."""
    result = recognize_best(case.text, intents, language="en")
    if result is None:
        return "miss", "no sentence matched"
    if result.intent.name != case.intent:
        return "suspect", f"matched {result.intent.name}, not {case.intent}"
    got = {k: _value(v.value) for k, v in result.entities.items()}
    time_text = got.pop("time", None)
    parsed = None
    if case.intent == "RemindAt" and time_text is not None:
        # packages/voice_reminders.yaml stores vp_reminder's task, not the raw slot
        parsed = vp_reminder(time_text, got.get("task", ""), got.get("day", ""))
        got["task"] = parsed["task"]
    expected = dict(case.slots)
    if case.intent == "RemindIn" and not any(k in expected for k in ("minutes", "hours")):
        return "suspect", f"matched with slots {got}, but no duration was said"
    if got != expected:
        return "suspect", f"slots {got}, expected {expected}" + (f", time {time_text!r}" if time_text else "")
    if case.clock is None:
        return "ok", ""
    if time_text is None:
        return "suspect", "no {time} slot"
    if parsed is None:
        parsed = vp_when(time_text, got.get("day", ""), case.prefer)
    if not parsed["ok"]:
        return "miss", f"vp_when found no time in {time_text!r}"
    clock = parsed["local"][11:16]
    if clock != case.clock:
        return "suspect", f"{time_text!r} read as {clock}, meant {case.clock}"
    when = datetime.strptime(parsed["local"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=NOW.tzinfo)
    if case.days is not None:
        if when.date() != (NOW + timedelta(days=case.days)).date():
            return "suspect", f"{time_text!r} read as {parsed['local']}, meant {case.days} day(s) from today"
    elif not NOW < when <= NOW + timedelta(days=1):
        return "suspect", f"{time_text!r} read as {parsed['local']}"
    return "ok", ""


def _load_verdicts():
    data = yaml.safe_load(VERDICTS.read_text()) or {}
    for text, entry in data.items():
        assert entry.get("verdict") in ("refuse", "gap"), f"{text!r}: verdict must be refuse or gap"
        assert entry.get("why"), f"{text!r}: say why"
    return data


@pytest.fixture(scope="module")
def results(intents, vp_when, vp_reminder):
    return [(case, *judge(case, intents, vp_when, vp_reminder)) for case in cases()]


def test_report(results):
    counts = {k: sum(1 for _, o, _ in results if o == k) for k in ("ok", "miss", "suspect")}
    print(f"\nswept {len(results)}: {counts}")
    for case, outcome, reason in results:
        if outcome != "ok":
            print(f"  {outcome.upper():7} {case.text!r}: {reason}")
    assert len(results) >= 300


def test_no_suspects(results):
    suspects = [f"{c.text!r}: {r}" for c, o, r in results if o == "suspect"]
    assert not suspects, "matched but wrong:\n  " + "\n  ".join(suspects)


def test_every_miss_has_a_verdict(results):
    verdicts = _load_verdicts()
    unpinned = [f"{c.text!r}: {r}" for c, o, r in results if o == "miss" and c.text not in verdicts]
    assert not unpinned, "pin a verdict in sweep_verdicts.yaml for:\n  " + "\n  ".join(unpinned)


def test_no_stale_verdicts(results):
    verdicts = _load_verdicts()
    swept = {c.text: o for c, o, _ in results}
    stale = [t for t in verdicts if swept.get(t) != "miss"]
    assert not stale, "these now match or are no longer generated; remove them:\n  " + "\n  ".join(stale)
