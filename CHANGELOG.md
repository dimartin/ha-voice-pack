# Changelog

## Unreleased

- **Music on an LLM pipeline:** the free-text "play" sentences now produce the pack's
  own `PlayMedia` intent instead of Home Assistant's `HassMediaSearchAndPlay`, which
  Home Assistant drops from local matching when the pipeline's agent is an LLM. It
  searches Music Assistant and plays the best match in the satellite's area, and says
  "I couldn't find X" when there is none. "play X" is matched too; genre and alarm-sound
  sentences still win over it. A named room ("play jazz in the kitchen", "play Nina Simone
  on the kitchen speaker") plays there, for genres and searches alike; the genre sentences
  need regenerating with `tools/ma_genre_sentences.py` for that. (issue #4)
- **LLM scripts for forecasts and reminders:** `script.weather_forecast` (day, rain) and
  `script.set_reminder` (task, and a time or minutes) hand a fixed sentence to the
  built-in agent, like `script.set_alarm`, and return what it said. (issue #5)

## 0.1.0 (2026-11-24)

The first release, and the set our own Home Assistant (2026.11.1) runs. The alarm
volume change has run there since 2026-11-17, the rest since 2026-11-24.

### What it does

- **Alarm clock:** one alarm, once or repeating (every day, weekdays, weekends), with
  snooze, stop versus cancel, skip the next ring, and four tones that repeat until
  stopped. It rings at `vp_alarm_volume()` (50% by default, clamped to 0-1) whatever
  the speaker was set to, then puts the speaker's volume back.
- **Reminders** at a time ("at 5 pm", "tomorrow at 9", "at 7 tomorrow evening") or
  after a delay ("in five minutes"), stored in a Local To-do list so they survive
  restarts.
- **Forecasts** for today, tonight, tomorrow and parts of the day, and rain checks.
- **Music:** "play rock" plays that Music Assistant genre; "play music by the band X"
  and phrasings that don't start with "play" use the built-in media search. Both play
  in the satellite's area.

### Time parsing

Times are parsed by `vp_when` in Jinja. It reads digits however speech-to-text writes
them ("935", "9.35", "5 30 pm"), number words, "quarter past six", "ten to nine",
"half six", "noon", "midnight" and parts of the day. A time with other words in it is
refused, so the reply asks again instead of guessing.

`vp_reminder` repairs reminders where the sentence matcher split the wildcards in the
wrong place, such as "ten" taken as the time in "remind me at ten to nine to call mom".

`tests/test_sweep.py` runs about 2,600 generated phrasings through Home Assistant's
sentence matcher and the parser. Before this release, 346 of them set a reminder or
alarm at the wrong time and still reported success. None do now. Every phrasing that
fails loudly has a recorded verdict in `tests/sweep_verdicts.yaml`.

### With an LLM conversation agent

Home Assistant offers every intent script to an LLM as a tool, but only with the name,
area, floor, domain and device class parameters. Scripts that need a time, day, task,
sound, snooze length or genre are therefore voice only (`platforms: [conversation]`).
The LLM sets alarms and plays genres through `script.set_alarm` and
`script.play_music_genre`.

### Known limits

- With an LLM agent as the pipeline's conversation agent, Home Assistant drops the
  pack's media sentences, so "could you play…" goes to the LLM (issue #4).
- The LLM has no script for forecasts or reminders yet (issue #5).

### Installing and upgrading

See the README's install steps. After an upgrade, reloading is enough:
`conversation.reload`, `intent_script.reload`,
`homeassistant.reload_custom_templates`, `script.reload` and `automation.reload`, plus
`input_boolean.reload`, `input_datetime.reload` or `input_select.reload` if those changed.
