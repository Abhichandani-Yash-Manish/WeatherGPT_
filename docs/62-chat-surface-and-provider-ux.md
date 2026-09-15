# The chat surface, and the key you paste: what the engine work looks like in the product — 15 September 2026

This round answers a fair criticism: the engine had grown a lot of capability that the page did not show, and
the risk of invisible work is that it is also unverified work. So this batch started with a read-only audit of
fourteen chat journeys against the live server, fixed what it found, and wired the artefacts into the
conversation. It also finishes the provider story: one command to paste an OpenRouter key, free models only,
ranked most capable first, with the local model as the fallback.

## What the audit found, and what was repaired

| Found | Repaired |
|---|---|
| **`table is not defined`** — a new renderer used a helper that only exists on the page object, so an answer carrying retrieval coverage failed to render at all | The retrieval account uses the shared table builder; the offline suite now renders one and asserts it |
| *"wave conditions off Kochi tomorrow"* asked **which place** (`needs_selection`) and listed four inland Maharashtra hamlets before the real Kochi | When candidates are genuinely tied on rank, the connected product decides (a wave cell exists only near the coast) and the reading is disclosed; a ranked preference still wins first, so Ahmedabad stays Ahmedabad |
| *"what is it like right now in Ahmedabad"* led with a **stale AWS row 29 km away** dated five months earlier | Fresh stations (≤ 3 hours) lead the reading and the sentence; the nearest station is named only when it is not the freshest, and a > 3-hour floor is stated as such |
| *"what is it like right now in Kochi"* resolved to a Maharashtra village because a station happened to be within 150 km | Tied candidates are scored by the distance to the *nearest fresh* station, so the Kerala city wins and the alternatives are named |
| English *"tomorrow morning"* = 09:30–12:30 but Hindi *"सुबह"* = 06:30–12:30: two different mornings for the same question | The day and part-of-day words now exist in all the scripts the editions use, with one definition per part of day; `\b` matching was replaced by a boundary that survives combining marks (Gujarati `સવારે` never matched before) |
| The answer trace said the interpreter was *"(local)"*, which would be wrong for any routed model | The trace names the provider, the model, the model calls and any failover |

## What is now visible in the conversation

Every answer offers only the generic actions plus the artefacts its own evidence supports:

- **Right now here** — the composed reading (station rows with distance and age, the published district day,
  the model hours next, and what is not connected), from any turn.
- **Write the alert brief** — on a warning turn, in the drawer, with the district, day, hazards as published,
  the issuer and retrieval instants, the CAP relay reported separately, the limits, and **Save to briefcase**.
- **Write the advisory brief** — on an agriculture turn, from the edition that turn read (region, crop and
  topic carried over), with the passages count, the forecast context kept apart, the conditions the source
  itself names, and Save to briefcase.
- **Write a briefing** — composes a briefing for the working place, writes it into this machine's series and
  offers the export; the Briefcase surface shows the newest run with its change reading.
- **What was retrieved, and what is missing** — pending slots with their reasons, the retrieval mode and
  candidate→returned counts, the product filters, the edition-comparison state and each edition's printed
  issue date and currency in words.

Everything else the packet carries (facts, passages with saved PDFs, charts, calculations, comparisons,
warning evidence, notes, sources, the machine record) already had a renderer; the audit confirmed it.

## The key, in one command

```sh
python3 scripts/models.py --set-key        # hidden prompt; writes data/runtime/model-config.json at mode 0600
python3 scripts/start_weather.py           # restart, so the running server reads the key
python3 scripts/models.py --probe-free     # optional: measure which free ids this account can actually reach
```

- **Free only.** Every routed id ends in `:free`; a paid id in configuration is *refused with a recorded reason*
  and can never be routed, by the client or the router.
- **Ranked, most capable first.** `data/registry/openrouter-free-models.json` holds twelve free ids in order of
  capability for this workload, each with why it sits there. The order is a judgement, said so in the file, and
  only a keyed probe turns it into a measurement.
- **OpenRouter first when a key exists, local model second.** Measured with a deliberately invalid key: the
  router tried OpenRouter, recorded `openrouter: the OpenRouter key was refused (HTTP 401)` as a failover, and
  the turn completed on the local model. No valid-key call has been made yet — that needs your key.
- **The key never leaves the machine or the log.** Setup writes it with owner-only permissions in a git-ignored
  directory and prints only the path and the mode; the settings surface shows whether a key is configured and
  where from, never the key.

The Settings surface now carries this as a **Model providers** card: the rules floor, OpenRouter's state and key
source, the ranked free list, any refused ids with reasons, and the two commands to copy.

## Evidence

`research/implementation/chat-surface-20260915/`: screenshots of the warning answer with the alert-brief drawer,
the advisory answer with the advisory brief, and the settings provider card; plus the action lists and drawer
text captured from the live page, and the key-flow acceptance transcript (mode 0600, no key printed, back to
*not configured* after removal).

## What this does not establish

- No browser acceptance beyond the journeys listed: one desktop viewport, one browser, keyboard and screen
  reader untested, mobile untested.
- No valid OpenRouter call: the free-model ranking is a stated judgment and the availability block stays
  `not_configured` until a real key is probed.
- The marine and right-now place probes trade a question for the product's own coverage rule. That is disclosed
  in the answer, but it is a heuristic with no coastline data behind it, and a place with no product cell and no
  fresh station still asks rather than guesses.
