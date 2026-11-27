# ha-voice-pack

Alarms, reminders and forecasts for Home Assistant Assist, answered by Home Assistant's
own sentence matcher instead of an LLM.

Assist has built-in timers but no alarm or reminder intent, and its weather intent only
reports current conditions. Ask a local LLM to "set a 9:35 alarm" and it can only say it
has no way to. This pack adds the missing intents as custom sentences plus intent
scripts, so these requests are handled locally, in well under a second, the same way
every time.

## What you can say

| Feature | Examples |
|---|---|
| Alarm clock | "set an alarm for 6:15", "set an alarm for one fifteen pm with chimes", "wake me up at 7", "when is my alarm", "cancel my alarm" |
| Repeating alarm | "set an alarm for 7 am on weekdays", "set a weekend alarm for 9", "wake me up at 6:30 every day", "skip tomorrow's alarm" |
| While it rings | "stop the alarm", "dismiss", "I'm up", "snooze", "snooze for 5 minutes", or the satellite's button |
| Alarm sound | "change my alarm sound to pulse", "what alarm sounds are there", "play the gentle alarm" |
| Reminders | "remind me to call mom at 5 pm", "remind me about the meeting in 2 hours", "remind me tomorrow at 9 to call the dentist", "remind me in five minutes to check the oven", "remind me to stretch in half an hour", "what are my reminders", "cancel the reminder to call mom", "cancel all my reminders" |
| Forecast | "what's the weather tomorrow", "what's the weather this evening", "what's tonight's forecast", "will it rain tonight", "do I need an umbrella" |
| Music | "play rock", "could you play some dance music", "put on some jazz": plays that Music Assistant genre. "play Nina Simone", "could you play some Nina Simone", "I want to hear Steely Dan": searches Music Assistant and plays the best match (an exact artist, album, playlist or track name first). Both play on the Music Assistant player in the satellite's area, on the built-in agent or an LLM one |

Replies sound like "OK, I'll remind you to call the dentist at 9:00 AM tomorrow." and
"Tonight: partly cloudy, 71 degrees, dropping to 60 by midnight."

## How it works

- **Times are parsed in Jinja, not by the LLM.** `{time}` is a wildcard, because
  speech-to-text writes "9:35" as "935", "9.35" or "nine thirty-five". `vp_when` in
  `custom_templates/voice_pack.jinja` reads digits, number words ("one fifteen pm",
  "seven oh five"), "quarter past six", "ten to nine", "noon", "midnight",
  "tomorrow", and part of day ("7 in the evening", "9 tonight"). With no am/pm, it
  picks whichever of morning or evening comes next. A time with other words in it
  ("the station at 5 pm") is refused, so the reply asks again rather than guessing.
  Relative reminders ("in five minutes") use number slots, which accept spoken words.
- **Wildcards can split in the wrong place.** In "remind me at ten to nine to call
  mom" the matcher may take "ten" as the time, and in "remind me to move the car at
  the station at 5 pm" it may take "the station at 5 pm". `vp_reminder` moves the
  stray words back where they belong before the reminder is stored.
- **Alarm clock:** one alarm, once or repeating (every day, weekdays, weekends).
  A bare hour from 4 to 11 means morning ("wake me at 7" said after lunch is 7 AM).
  When it fires, it plays the chosen tone, says the time, then repeats the tone with
  a short gap until stopped, snoozed or cancelled (5 minutes at most). Before each
  tone it waits for the satellite to be idle, so it doesn't talk over you. If
  `vp_media_player()` names the satellite's speaker, it rings at `vp_alarm_volume()`
  (50% in the example) whatever the speaker was set to, so a speaker left near 0%
  still wakes you, then the speaker's volume is put back. "Stop" ends this ring; a repeating
  alarm moves to its next day. "Cancel" turns it off. Snooze moves only the next
  ring, so a snoozed 7:00 weekday alarm is back at 7:00 the next day. If Home
  Assistant was down at alarm time, it rings on startup if that was in the last 15
  minutes. There are four tones
  (classic, chimes, pulse, gentle), chosen with `input_select.wake_alarm_sound` or
  by voice. `script.set_alarm` lets the LLM set an alarm for phrasings the sentences
  miss, through the same parser.
- **Reminders** are items with a due time in `todo.reminders`, a Local To-do list, so
  they survive restarts and show up in the To-do panel. Items added there with a due
  time ring too. Nothing polls: the "Voice reminders" automation keeps
  `input_datetime.voice_reminder_next` at the earliest due item, speaks everything due
  when it fires, and marks those items completed. It also catches up after a restart.
- **Forecasts:** today and tomorrow use the daily forecast. "Tonight" and "this evening"
  use hourly rows from 5 PM (or now, if later) to midnight.

## Install

Needs Home Assistant 2026.9 or later, a satellite that supports announcements, and a
weather entity with daily and hourly forecasts (Met.no has both).

1. Copy `custom_sentences/en/*.yaml`, `packages/*.yaml` and
   `custom_templates/voice_pack.jinja` into the same folders under `/config`, and
   `sounds/*.mp3` into `/config/www/voice_pack/`. `sounds/make_sounds.sh`
   regenerates the tones with ffmpeg (which the Home Assistant container ships).
2. Copy `custom_templates/voice_pack_config.example.jinja` to
   `/config/custom_templates/voice_pack_config.jinja` and set your satellite,
   weather entity, the satellite's speaker and alarm volume, and the snooze
   length. To stop alarms with the satellite's button, copy
   `examples/voice_pack_button.yaml` to `/config/packages/voice_pack_local.yaml`
   and set the button entity.
3. Enable packages in `configuration.yaml`:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
4. Add a Local To-do list named "Reminders" (Settings → Devices & services → Add
   integration → Local To-do), so that `todo.reminders` exists.
5. Restart Home Assistant. After later updates, reloading is enough: `conversation.reload`,
   `intent_script.reload`, `homeassistant.reload_custom_templates`, `script.reload` and
   `automation.reload` (plus `input_boolean.reload`, `input_datetime.reload` or
   `input_select.reload` if those changed).
6. Music genres (needs Music Assistant): run `tools/ma_genre_sentences.py` inside the
   Home Assistant container (`docker exec homeassistant python3 /tmp/ma_genre_sentences.py /config`).
   It writes `custom_sentences/en/music_genres.yaml` and
   `custom_templates/voice_pack_genres.jinja` from Music Assistant's genres with at
   least 5 tracks. Rerun it when genres change, then reload conversation and custom
   templates. Give each Music Assistant player an area.
7. Optional: expose `script.set_alarm`, `script.set_reminder`, `script.weather_forecast`
   and `script.play_music_genre` to Assist if you use an LLM conversation agent.

Home Assistant also offers every intent script to an LLM agent as a tool, but only with
the parameters name, area, floor, domain and device class, whatever the sentences fill.
So the scripts that need a time, a day, a task, a sound, a snooze length or a genre are marked
`platforms: [conversation]`: voice only, hidden from the LLM. Otherwise "is it going to
rain tomorrow?" reaches the forecast script with no day, and gets today's forecast. The
scripts that take no slots (cancel, dismiss, skip, status, list) stay available as tools.
The scripts in step 7 have real fields, so they are the LLM's way in. Each returns the
sentence to say, built from what was actually done, never worded by the model; the alarm,
reminder and forecast scripts get it by handing a fixed sentence to the built-in agent.

The pipeline must have "Prefer handling commands locally" on, or every request goes
to the LLM first.

## Credit

Snooze, repeating alarms, skip-next, setting the alarm's volume, ringing after a restart and
the hardware-button stop come from [Voice Alarms](https://github.com/Gamer92000/hass_alarm),
[HA Alarms](https://github.com/nathothan/HA-Assist-Alarms) and
[HA Alarm Clock](https://github.com/nirnachmani/HA-Alarm-Clock). Those are custom
integrations (the first works through an LLM agent only). This pack does the same
things with sentences and Jinja. For reminders,
[ha-voice-reminders](https://github.com/peerloomllc/ha-voice-reminders) takes the
same approach as this pack and goes further (recurring reminders, dayparts, phone
push).

## Tests

```sh
pip install -e ".[dev]"
pytest -q tests
```

`tests/test_sentences.py` runs every example phrasing through hassil's
`recognize_best` (Home Assistant's sentence matcher, pinned to the version HA ships).
It checks the intent and slots, and
that no two files define a shared list differently. Home Assistant merges all custom
sentence files into one namespace, so a second `day` list would silently replace
another file's list.

`tests/test_time.py` renders `vp_when` and `vp_reminder` with plain Jinja2, against a
fixed clock and stubs of Home Assistant's template helpers.

`tests/test_sweep.py` generates about 2,600 reminder and alarm phrasings and runs
each through the matcher and the time parser. A phrasing that matches but would
store the wrong time or task fails the test. One that doesn't match needs a verdict
in `tests/sweep_verdicts.yaml`: `refuse` (correct to leave unmatched) or `gap`
(should work, doesn't yet). `pytest tests/test_sweep.py -s` prints the report.

The intent scripts need a running Home Assistant. To check a live install without
running anything, call the websocket command
`{"type": "conversation/agent/homeassistant/debug", "sentences": [...]}`. To run the
intents for real, use `conversation/process` with `agent_id: conversation.home_assistant`.

## Limits

- One alarm at a time (repeating or not).
- "Stop" on its own stays Home Assistant's media pause; say "stop the alarm".
- Alarms and reminders ring on one satellite (`vp_satellite()`), not the one that
  heard the request.
- English only.
- With an LLM conversation agent, Home Assistant drops a local match of its own
  `HassMediaSearchAndPlay` or `HassGetState` and hands the request to the LLM
  (`_async_local_fallback_intent_filter` in `assist_pipeline`). The pack's media
  sentences use their own `PlayMedia` intent for that reason. Home Assistant's built-in
  state questions still go to the LLM.
- The built-in agent answers an action on a device in the satellite's own area with a
  beep instead of speech. The pack's intent scripts target no device, so their replies
  are always spoken.
