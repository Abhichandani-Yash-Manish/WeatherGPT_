# 138 — The demo runbook

SIH26068, team Void Pointer. Laptop browser, projected, with a recorded run as the backup.

Everything below was measured on this machine on 21 September 2026 against the running engine. The
timings are what the ten beats actually took, not estimates.

---

## Before you leave

```bash
cd ~/WeatherGPT                       # after scripts/move_off_desktop.sh
python3 scripts/verify_all.py         # 21 steps, 0 failed
scripts/install_daily_schedule.sh --verify
```

Then record a fresh backup, because the backup is only worth having if it is today's:

```bash
python3 -m weathergpt_data.workspace --port 8765 &
cd frontend && node tools/demo.mjs    # ~3m20s, writes research/demo/weathergpt-demo-<stamp>.webm
```

Watch the run. If a beat says `no answer`, that beat is the one to fix or drop — not to discover on
stage. The recording is a real run: every turn in it was planned, retrieved and written live.

## On the day, in order

```bash
cd ~/WeatherGPT
python3 -m weathergpt_data.workspace --port 8765
```

Open `http://127.0.0.1:8765`. Check the top right shows a place and the rail lists conversations.
Ask one throwaway question before the judges arrive — the first turn of a cold process is slower
than the rest, and it should be spent on nobody.

**Have the recording open in a second tab, paused at 0:00.** If the network, the provider or the
laptop misbehaves, switch to it and keep talking. Do not debug in front of judges.

---

## The ten beats

`node tools/demo.mjs --list` prints this running order; the tool drives exactly these.

| # | Key feature | Ask | What to point at | Took |
|---|---|---|---|---|
| 1 | KF1 real-time retrieval | What is it like right now in Ahmedabad? | The station is **named**, with its distance from the point asked about. Not "Ahmedabad" — a station, 7.45 km away. | 16s |
| 2 | KF2 natural-language forecast | Will it rain in Mumbai tomorrow? | Plain question, plain answer, and the value carries its window and its source. | 15s |
| 3 | KF3 NWP models (GFS) | Compare the GFS and best-match forecasts for Pune tomorrow. | Two **named** models. Where they disagree it says so rather than averaging them into one number. | 18s |
| 4 | KF4 warnings, early warning | Which districts in Odisha have a warning today, and in what colour? | The publisher's own colours. A district with nothing published is never drawn green. | 57s |
| 5 | KF5 location-based advisory | What does the agromet advisory say for Ahmedabad? | The bulletin's **own words**, quoted, with its issue number and date. | 27s |
| 6 | KF6 Indian languages | अहमदाबाद में कल बारिश होगी क्या? | Answered in the script it was asked in. The place, the dates and the units are not translated. | 13s |
| 7 | KF7 climate and history | Which year was the wettest in the record for India? | A year and a figure — 1917, 1488.8 mm — from the published record. Not a range, not a guess. | 13s |
| 8 | KF8 evidence under the answer | Where did that number come from? | "That number" is understood. The follow-up names the series the figure came from. | 9s |
| 9 | Refusal discipline | Is flight AI-101 on time? | It says it cannot and why. **It does not invent a plausible answer.** | 12s |
| 10 | Refusal discipline | Is it safe to go out in Chennai right now? | It gives the conditions and the warning in force, and declines the safety judgement. | 19s |

Beat 4 is the slow one — it sweeps a state's districts. Talk over it: that wait is a real national
sweep, and saying so is better than apologising for it.

## The two beats that win it

Most demos in this category cannot refuse. Beats 9 and 10 are worth more than any forecast, because
every judge has seen a chatbot confidently invent a flight time.

Say it plainly: **this workspace has no flight source, so it says so.** Then beat 10: it has plenty
to say about Chennai, says all of it, and still will not tell you whether to go out — because "safe"
is a judgement about you, not a measurement it holds.

## If a judge pushes

- **"Is it just an LLM wrapper?"** The model plans the turn and writes the sentence. It never
  supplies a number. Every value on screen came from a retrieval, carries its source id and the
  instant it was read, and the written answer is checked against that evidence before it is shown —
  an answer that states a figure the evidence does not support is rejected, not published.
- **"What if the model hallucinates?"** Open the fold under any answer. The claim, the source, the
  window and the retrieval time are tool-owned; the prose is the model's. Ask beat 8 live.
- **"Does it work offline / without the internet?"** The evidence store is local. Show a surface —
  Today reads 756 districts from this machine.
- **"Voice?"** Implemented, and the README says exactly what has and has not been validated: no
  noisy-field testing and no native-speaker acceptance yet. Do not overclaim this one.
- **"Which parts are not finished?"** README §"Where this stands" is deliberately honest and lists
  them. Saying it first is stronger than being caught by it.

## Known rough edges — say them before you are asked

- Advisories and agromet are the weakest group in the scenario atlas (60–76% against 89% overall).
- Warning delivery to a real device has never been demonstrated end to end.
- Language output is measured per direction but not yet accepted by a native speaker.
- WRF is not connected. GFS is. The problem statement names both; claim only the one that is true.

---

## The numbers, if asked

| | |
|---|---|
| Scenario atlas | 273/306 (89%), 306 turns, run against the engine on HEAD |
| Refusal rate | 9% — 11 upstream (the publisher has no such data), 1 product limit, 16 avoidable |
| Python tests | 1539 |
| Frontend specs | 81 suites, 538 checks |
| Verification gate | 21 steps, 0 failed |

The refusal breakdown is the honest one to quote: most refusals are the publisher having nothing,
not the product failing.
