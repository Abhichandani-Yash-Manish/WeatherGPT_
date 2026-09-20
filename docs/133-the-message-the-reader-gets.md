# 133 — The message the reader gets

21 September 2026. The complaint was that the chat had no natural conversational flow, that the answers
were framed by the machine rather than for the reader, and that this was the weakest part of the product.
The batch before this one ([docs/132](132-the-model-writes-the-answer.md)) had already moved the writing
to the model and measured it: one answer in eleven model-authored before, eight after, across eleven
intents. That was true and it was not enough, because what the model was *given* was a database, what it
was *allowed* was narrower than what it was shown, and what it was *told to append* repeated itself.

Everything below was measured on the live engine on this machine, against the configured provider, before
and after each repair. The battery is `tmp/battery.py` (twelve single questions across twelve intents plus a
follow-up pair) and `tmp/battery2.py` (eight real conversations, four of them multi-turn); both are in the
working tree and both print the table the numbers below come from.

## 1. What was actually wrong

### 1.1 The station fields a reader means were never read

    Q  What is it like right now in Surat?
    A  At SURAT · 13.37 km from the requested point, the 20 Sep 2026 22:00 IST observation shows
       wind speed 0.0, wind direction 0.0, and pressure 1009.0.

The product held, for that station and that instant: **26 °C, 94 % humidity, mist, 3 km visibility, a few
clouds, a calm wind**. The conversation path read only three of the nine fields the station reported, and
the three it read are the least useful three a reader asking "what is it like" could be given.

The cause is a spelling. The two station layers print the same measurement differently and neither says so:
the METAR layer (S63, `imd:metar_data_layer`) prints `temp`, `rh`, `windsp`; the AWS layer prints `temp`,
`rh`, `windspeed`. The tuple in `observation_tasks` accepted `temperature_c` and `humidity` — the product's
own names, which neither layer emits — so a METAR could never produce a temperature or a humidity fact. The
wind and the pressure matched only because their spellings happened to be the layer's. The unit went with
it: a fact carried no unit at all, so the composer wrote "visibility 3000.0" and "a dew point of 25" into
prose, and the check downstream cannot police a unit the fact does not carry.

### 1.2 The right-now reading's own hours were prose, not evidence

The same reading composes the model's next hours — 25.5 °C, a 0 % rain chance, 0.0 mm — and, until this
batch, those values reached a reader only inside a block of text. They were in the composed summary and in
no fact, so a model writing the answer could not see them and no claim could cite them. The temperature a
reader most wants for "what is it like" was unreachable by construction.

### 1.3 A follow-up that broke the conversation

    Q  What is it like right now in Surat?
    Q  and tomorrow?
    A  The task could not retrieve verified evidence: No supported parameters requested:
       2.3 s, status unavailable

"and tomorrow?" is the most ordinary thing a reader types. The window moved correctly, the operation
correctly stopped being an observation (docs/116 §2 fixed that), and the new forecast inherited the
observation's empty parameter list — because an observation reads a fixed station field set and carries
none. A point forecast with no measures is not a question the tools can answer, so the reader's follow-up
came back as a retrieval failure.

### 1.4 "why?" was answered with a false statement about this workspace

    Q  Is there any warning in force for Patna?
    Q  why?
    A  Because I can't verify any weather value, forecast, warning, observation, date, time or
       place-specific fact this turn — no source is wired to this chat, so I have no evidence to draw on.

Two defects in one sentence. "why?" after a turn that had just read a warning bulletin was classified as
small talk, so it never reached the evidence the workspace had stored seconds earlier. And the small-talk
path handed the model a workspace picture whose `sources.wired_to_chat` list was **empty**, because that
flag is nested under `connector` in the ledger and the brief read it at the top level. The model was not
inventing; it was repeating a false input. A conversational reply is allowed to be vague. It is not allowed
to be confidently wrong about what this product can do.

### 1.5 The answer said its caveat twice

    No rain is forecast for Ahmedabad tomorrow: rainfall of 0.0 mm is expected over the window ...
    That figure is a model forecast for the place point, not an observation or a district average,
    and the source model run time and local representativeness remain unverified. ... These are model
    forecasts for the selected points, not observed conditions or district averages. Source: GFS
    forecast; conditions can change.

Two mechanisms put a caveat in front of a reader: the model writes it from the limits it was given, and the
engine appends a held clause afterwards if the prose did not carry it *verbatim*. The test was a substring
test, so a paraphrase never matched and the clause was appended anyway. The same phrase reached the reader
twice in 109 words — and, measured by the card batch working beside this one, **481 of that reply's 667
characters (72 %) were caveat-said-twice or a place note the packet already carried as fields**.

### 1.6 Widening what the model could see made the answers right and long

Fixing §1.1 and §1.2 turned nineteen facts loose on the composer and the very next answer named eleven
separate measures:

    ... 26 °C, mist, 0.0 kt wind, 94.0% humidity, a dew point of 25, pressure 1009.0, visibility
    3000.0, and a few clouds at 2000 feet; scattered clouds at 8000 feet. ... 25.5 °C with a 0 % rain
    chance and 0.0 mm rainfall for 22:00–23:00, then 25.4 °C ... with wind 3.1 km/h and 3.7 km/h ...

`docs/117` §3.2 and §3.3 asked for exactly this to be prevented — "Summarise a retrieval, never recite it",
with a numeral budget as the gate — and it had never been built. The numeral ratio is the wrong instrument
for it: that answer sits at **0.20 numerals per word**, well inside the budget `within_budget()` already
enforces, because a list of twenty small numbers among a hundred words is not a high ratio. What it is is
thirteen measures when the reader asked for one thing.

## 2. What was built

| # | Repair | Where |
| --- | --- | --- |
| 1 | Every spelling the two station layers print is read, and present weather as words | `observation_tasks.FIELDS`, `TEXT_FIELDS` |
| 2 | Each station parameter carries the unit it is *read in*, marked as such | `observation_tasks.READ_IN_UNITS`, `unit_source` |
| 3 | The right-now model hours are forecast facts with a window and a source | `observation_tasks._hour_facts` |
| 4 | The opening sentence states the hours and says they are grid-cell output | `leadline._next_hours_clause` |
| 5 | A point forecast with no named measure gets the measures a reader means | `dialogue.CORE_FORECAST_MEASURES` |
| 6 | A bare explanation request reaches the stored evidence instead of small talk | `dialogue.EXPLAIN_ONLY` |
| 7 | The explanation is written for the reader, behind the same checks as any answer | `conversation._ask` |
| 8 | A caveat the answer already carries is not appended under it | `leadline.carried_by` |
| 9 | The composer is handed the answer's material, not every retrieved row | `conversation.composer_evidence` |
| 10 | A series longer than three rows reaches the composer as its range | `COMPOSER_SERIES_ROWS` |
| 11 | The composer sees a window in words and no raw instant | `conversation.composer_fact` |
| 12 | A recitation is sent back to the model once with its own shape named | `conversation.written_answer` |
| 13 | A conversational reply may not deny this workspace's own wiring | `conversation.CHAT_WIRING` |
| 14 | The workspace picture reads `wired_to_chat` where the ledger keeps it | `workspace_brief._ledger_rows` |
| 15 | A range across years is no longer stated as one year | `leadline._history_sentence` |
| 16 | A refusal names the number it refused | `conversation.generated_answer_problem` |

Three of these are worth their own paragraph.

**The composer now receives the answer's material and not the database** (§2, repairs 9–11). The measures
that answer the question are ranked — a parameter the question named leads, then the reader's own order,
temperature and sky before pressure — and a series longer than three rows arrives as the range the renderers
already compute. The rest travels in the same payload under `further_evidence`, named and citable, because
withholding it would be a different lie. `composer_floor` strips the held clauses from the text the model is
handed, so it cannot echo a sentence the engine is going to append anyway.

**A detail I measured and did not lose:** an earlier version of the range replaced the rows it summarised in
the material but left them in `further`, so the composer was handed the summary *and* the series. The spec
`test_the_rest_travels_with_the_answer_rather_than_being_withheld` caught it.

**The numeral budget was replaced by a shape, not a threshold** (repair 12). `series_recited` counts how
many separate measures the prose names and how deep into one series it went, and the first attempt that
goes over is sent back to the model with its own draft's numbers quoted at it — one retry, then the floor.
That is the difference between a product that gives up on the model and one that works with it, and it is
what §1.6 needed: widening what the model can see is right, and the discipline belongs in the loop.

## 3. What a reader gets now

Measured on the live engine at the end of the batch: **14 of 14 answers model-written**, median 4.7 s.
(The latency figures in this section were taken while two other batches were building on the same machine;
the same two questions re-measured in isolation take 5.7 s and 6.4 s.)

| question | before | after |
| --- | --- | --- |
| *What is it like right now in Surat?* | wind 0.0, direction 0.0, pressure 1009.0 | 26 °C, mist, 94.0 % humidity, and the model's own next hours said to be grid-cell output |
| *and tomorrow?* (after that turn) | 2.3 s, `unavailable`, "No supported parameters requested" | answered; 5.3 mm total, 26.3–31.1 °C, 72–94 % humidity over the window |
| *why?* (after a warning turn) | "no source is wired to this chat" | a real explanation of the day-2 row, 2.8 s, model-written |
| *Will it rain in Ahmedabad tomorrow?* | 109 words, the caveat twice | **45–61 words**, the finding first, the source named once |
| *Show the annual rainfall trend for Ahmedabad 1981–2010* | refused: "it introduced a number that is not in the retrieved facts: 54.7" | answered: 81 words, the slope, the range, and what the slope is not |
| *Air quality in Delhi today?* | 199 words, 41 numerals, opening on a place label | 111 words: the index, its 24-hour range, PM2.5 and PM10, and the four remaining pollutants as ranges |

The last row of that table is the one I would keep. It is still the longest answer in the battery, it still
names six measures, and it is at the cap rather than under it — but it states a *shape* (an index, a range,
a peak hour) instead of reciting two hundred rows, and it says which rows are readings and which are model
output for a grid cell.

## 4. What this does not claim

- **The 14-of-14 is fourteen questions, not a survey.** They are twelve intents plus two follow-ups, asked
  once each, against one provider (`deepseek-chat`) on one machine. A different provider, a cold cache or a
  planner that reads a question differently will move it. Nothing here establishes forecast skill,
  operational clearance or PS compliance.
- **The recitation check is a shape, not a judgement.** It counts measures and depth. An answer can stay
  inside both numbers and still be clumsy, and an answer that is genuinely about many measures is sent back
  once before it gets through. The threshold (`6` measures, `3` values deep) came from this batch's own
  measurements and would want more evidence before it is treated as settled.
- **One repetition I did not fix.** `district_warnings.summary()` states "not an all-clear" and the warning
  path's held clause states "an absence of matching official guidance is not an all-clear". Both are
  load-bearing and both are asserted by specs on the warnings *surface*, which does not go through the
  composer at all — removing the phrase from the shared summary to stop the conversation path repeating
  would have taken an honesty sentence off a served surface. So the phrase still reaches a reader twice on
  a warning turn, and the two sentences say different things: one is about this bulletin, one is about
  the absence of guidance. Recorded rather than papered over.
- **The composer's ranking is a list in code.** `COMPOSER_MEASURE_ORDER` was set by hand from what a reader
  asks for; the only empirical support is that the model planner independently chooses the same four
  measures for an unmeasured weather question across four phrasings, measured today. It is a serving
  decision with the standing of a threshold, not a finding.
- **Nothing was checked in a language other than English** in this batch. The composer's prompt and the
  held-clause dedupe are language-agnostic by construction, and `carried_by` matches on Latin tokens, so a
  Hindi answer's caveat is not deduped at all — it will still be appended, which is safe and repetitive in
  the way §1.5 was. That is the next thing to measure, and `docs/30` owns the gate it would have to pass.
