# 144 — The model answers, and the sources open up

> **The direction.** *"The LLM layer is the key and most intelligent part here and I shouldn't be
> hindered or face problems due to the data layer — it should be given freedom to a maximum extent…
> and the LLM layer should answer and its capabilities should be used to the max."* Plus: unblock the
> underlying data sources, because not all of them are being used.
>
> **What was found.** The principle was violated in exactly one place, and it was backwards: the model
> was denied the answer precisely when the retrieval was richest. And the data layer was both better
> and worse than the ledger said — eight "unconnected" sources were already connected, while the best
> one in the registry had sat unused for six days.

Written 22 September 2026, the last technical batch before the demo.

---

## 1. The model was locked out of its best answers

`written_answer_applies` refused to let the model write whenever a turn carried more than six
passages. Measured against the live engine before touching anything:

| question | passages | who wrote it |
|---|---|---|
| What does the All India Weather Summary say today? | **12** | **TEMPLATE** |
| Summarise the extended range forecast | **8** | **TEMPLATE** |
| What does the agromet advisory say for cotton in Rajkot? | 3 | model |
| What does the sea area bulletin say for the Arabian Sea? | 4 | model |

The more a turn retrieved, the more certain the reader was handed a table. The two questions that
lost were the "what is the big picture" questions — exactly the ones a demo asks.

This is the same backwards reasoning docs/132 removed from the *length* gate ("a long, stiff,
table-shaped floor is exactly where a reader gains most from prose") and left standing here. The
stated worry was real — a turn with more passages "cannot be written without quietly dropping the
rest" — so the fix answers it rather than ignoring it:

- the leading passages go to the model **in full**, as before;
- the rest go **by name** as `further_passages` (section, stage, page), so the answer can say what
  else the document covers instead of writing as though it ended at passage six;
- those named passages are explicitly **not quotable and not citable**, and the verbatim-restoration
  step ignores them — appending words the model never saw would be putting them in its mouth, and
  would rebuild the wall of header text docs/132 removed.

Three more things were in the way, each found by fixing the one above it:

- **The citation instruction only named facts.** A document turn carries passages and *no facts at
  all*, so the model read "cite the facts you used" as "nothing to cite" and was rejected for
  omitting every evidence reference. It now names passages explicitly.
- **A draft that only forgot to cite is asked again**, not discarded. Citing nothing is a
  bookkeeping slip, not an unsafe answer — the prose had already passed every number, unit, place
  and language check. Throwing that away for an empty id list and handing over a table is the worst
  trade available.
- **The floor travelled whole in the prompt**, so a ten-passage turn blew the 7000-character
  authoring ceiling. The payload is now bounded independently (`MAX_FLOOR_IN_PAYLOAD`), which is
  what that ceiling was really a proxy for, so it rose to 20000.

**Result, same questions, same engine: 7 of 8 model-written, including the 12-passage and 8-passage
turns.** The one failure was `No model provider` — both free tiers rate-limited at once under rapid
probing, which is a demo risk recorded in §5 rather than a code defect.

## 2. A whole family refused while holding current data

"What does the Gujarat state agromet bulletin advise?" → **unavailable**, zero passages. The corpus
held two Gujarat editions:

```
doc 22678bac94  Gujarat  issue 2026-09-12   257 passages
doc 52840df7cf  Gujarat  issue 2026-09-19   216 passages   <- current
```

Retrieval ranks across every edition and only *then* retires the superseded ones. A generic question
matched the older edition's wording, all of it was retired, and the turn refused — with 216 current
passages sitting unread. That is the whole `state_agromet` family, 1,106 passages across five
states, able to refuse while holding current data.

**The engine now asks the current edition before refusing.** This is the general shape the turn loop
could not previously do — when a retrieval comes back with nothing servable, ask again somewhere
better rather than reporting an absence — and "somewhere better" is exactly defined as the newer
edition of the same product and region, so it widens nothing. A genuine absence still refuses, and
now says both things: that an older edition matched, and that the current one does not.

Gujarat: **unavailable / 0 passages → partial / 10 passages, model-written.**

## 3. The data layer: better and worse than the ledger said

The ledger was compiled **16 September** and had not been rebuilt since. It reported ten sources
`reachable_not_connected`; **eight of them were already connected** as document families. The corpus
actually holds **8,473 passages across 12 families** — national bulletin, flash flood (national and
South Asia), extended range, press release, sea-area, coastal, special advisory, state and district
agromet — all reachable from chat. Rebuilt: **21 active, 8 reachable-not-connected, no stale endpoints.**

### What was genuinely unused was the best thing in the registry

**S16/S17 Mausamgram** — IMD's *own* public multi-model forecast, **no credential** — had been
carried since 16 September as "the only multi-model source in the registry" and nothing used it.
Every forecast this product served came from a global model through Open-Meteo. It is now the
`imd_forecast` capability:

```
temp, temp_bc (bias-corrected), apcp, rh, wspd/wdir/gust,
wspd80m/100m/120m, tcdc, ghi        3-hourly to 120 hours
```

Two things the source does not supply, both stated rather than filled in:

- **No grid identity.** But the grid is not a mystery — the address names it (`_0p125`) and the
  publisher answers *only* on exact multiples. Pune at 18.520/73.860 returns `{"error":"No data
  found"}`; 18.500/73.875 answers. So the request is snapped to the publisher's own grid and the
  answering cell and its distance are named, like every other point source here.
- **No time axis.** Each sample's valid time is derived from the requested initialisation plus its
  three-hour step, and every record's locator says so. A derived time is never presented as a
  printed one.

Live: *"What does IMD itself forecast for Pune tomorrow?"* → 22.8–28.5 °C raw, 24.4–32.2 °C
bias-corrected, 5.6 mm total, served from the cell 3.0 km away.

### The blocked API was not the only route to the blocked products

Fifteen `api.imd.gov.in` products are credential-gated. Most already had substitutes. The registry
recorded three real gaps; probing the **same credential-free GeoServer this workspace already uses**
for the warning layer and the AWS stations found them:

| Blocked | Public layer | Outcome |
|---|---|---|
| **S03 district nowcast** | `imd:NowcastWarningDistrict` | **connected** — 764 districts, issued today |
| S39 AWS station data | `imd:aws_data_layer` | already connected via `observations.py` |
| S41 district rainfall | `imd:subdiv_rainfall_now` | probed, 36 subdivisions — reported, not built |
| S43 cyclone track | `imd:Cyclone_Track_V` | probed, served no JSON — reported |

**The nowcast is a different product from the district warning and that is the point.** The warning
layer is a five-day outlook keyed to the bulletin day; the nowcast is a short-validity statement —
Pune's was issued 16:00 and valid to 19:00. Answering "is a storm about to hit" from the five-day
outlook answers a different question.

One correction made during the build, and it matters. The `cat1..cat19` columns look like hazard
flags and mostly hold their own index. They are **not all flags**: five West Bengal districts carried
the entire nowcast sentence in `cat16` while `message`, `impact` and `action` were empty, and Pune
carried `cat7`/`cat9` with no text anywhere. Reading those numbers through the *district warning*
product's hazard table would have answered **"Pune: dust-raising winds, heat wave"** on nothing but
two indices matching a different product's numbering. So the codes are carried as codes, the text is
carried as text, and neither is given a name this source did not print.

### The cyclone products, and which of them could actually be read

RSMC New Delhi publishes cyclone material on the same public host whose sea-area and coastal
bulletins this pipeline already ingests. All three candidates were probed:

```
uploads/No Cyclone.pdf              discovered, 192 KB, NO TEXT LAYER - a map image
uploads/archive/73/..._splbltn.pdf  discovered, special bulletin, NO TEXT LAYER
uploads/archive/22/..._SAT_BLTN     discovered, extracted, 3 passages   <- registered
```

Discovery works for all three; extraction refuses the first two, which is the pipeline behaving
correctly on an image-only PDF. **One family was registered, not three.** A family that can never
produce a passage is not coverage, and shipping two of them would have been claiming it. Reading
them needs OCR, which is not in the reviewed path; the cone geometry has no substitute at all and is
not claimed.

## 4. The nowcast, and the last place the model was locked out

The nowcast's evidence is neither a fact nor a passage — it is the publisher's own rows — and three
separate layers assumed evidence meant "facts or passages":

1. `written_answer_applies` read `has_evidence` that way;
2. the composer payload had nowhere to put it;
3. **the dispatcher never merged `nowcast_records` up from the task packet**, so even after the
   first two were fixed the composer received an empty list.

All three are closed, and the single product whose answer is entirely the publisher's *words* is no
longer the one product a model was never asked to write. It now reads:

> Yes — IMD has a nowcast running for KOLKATA, WEST BENGAL, issued at 1544 IST on 2026-09-22 and
> valid until 1844 IST, with the colour given as orange. The entry carries category codes 2 and 4,
> but no legend is published with this layer, so those codes are not named here and are not the
> district warning product's hazard codes. … it is reference only — no dissemination is authorised,
> and an absence would not be an all-clear.

One defect found on the first live run: the expiry was set to the *retrieval* time, which is already
past by the time an answer is assembled, so every nowcast came back `stale` with its evidence
intact. It now expires on the publisher's own printed `vupto` clock.

## 5. Measured, and the risks worth naming before a demo

- **1,616 tests passing**, no regressions.
- Sources: **21 active** (was 20), stale endpoints **0** (was 1), the ledger rebuilt from 16 → 22
  September with every connected family reconciled against the code that ingests it.
- Two new capabilities the planner can reach: `imd_forecast` and `nowcast`, both routed correctly by
  the model on first try from natural questions.

Three risks, stated rather than discovered on the day:

1. **Both free LLM tiers can rate-limit at once.** The chain is deepseek → openrouter → ollama, and
   ollama is not configured on this machine. When both free tiers refuse, every answer falls to its
   template. Configuring a local Ollama model would give a guaranteed-available floor; it is the
   single highest-value demo insurance and it is not installed.
2. **S16's registry address pins a model run.** The probe is green because it points at a published
   run; runs expire, so that row will read `stale_endpoint` again in time. The *connector* drives
   itself from the current 00/12 UTC boundary and walks back, so the product is unaffected — but the
   ledger row will need re-pointing, and that is a maintenance trap rather than a fixed thing.
3. **The nowcast category legend is genuinely unknown.** The answers say so. If a legend is found,
   naming the codes is a small change and a real improvement; until then the numbers stand unnamed.

## 6. Does the model actually weigh the new sources? Measured, not assumed.

The principle this batch was judged against is that the model reaches the new sources, weighs their
outputs against each other, and decides what to use. Asked directly, the honest answer at first was
*partly*, and the gaps were specific.

**It weighs well when the plan carries more than one source.** Asked to compare IMD with the global
model, it wrote: *"The two global sources differ by −5.3 mm on rainfall (best-match minus GFS), so
the spread between them is larger than the gap between either and IMD."* That is real comparative
reasoning, not two tables side by side.

**But it fell to the template half the time doing it.** Six runs of the same comparison: three
model-written, three refused with *"a measurement does not match its source unit"* — a message that
named nothing. Made to name its culprit, it said **`5.3 mm`**: the crosscheck computes a signed delta
of −5.3 mm, and the model wrote "they differ by 5.3 mm", which is how a person says it. The magnitude
of a signed quantity this product itself computed is the same measurement, not an invented one. This
is the third time a check that was right for single-source turns became wrong once the evidence got
richer — after the measurement check on "acephate 75 % SP" and the link check on the bulletin's own
Play Store URL (docs/132, §1 above). **6 of 6 model-written after the fix.**

**And it was not reaching for the independent source where it mattered most.** Asked *"which source
should I trust?"*, it planned `forecast lookup` + `forecast crosscheck` — and crosscheck compares S21
and S62, which this product's own capability record describes as *"can share GFS lineage, so not
independent validation"*. It compared two sources that may be the same model and left out Mausamgram,
the one connected forecast not derived from it. A reliability, trust, confidence or comparison
question now adds `imd_forecast` alongside. Not because IMD is ranked higher — nothing here ranks a
source — but because it is what makes the comparison worth making. It now answers:

> No single source is more trustworthy here: IMD Mausamgram is a multi-model blend published by IMD,
> but it is model output, not an observation… The best-match and GFS figures may share upstream
> lineage, so their agreement would not be independent confirmation, and neither an average nor a
> confidence score is produced.

### Then the threshold was moved, because it was the wrong one

The comparison firing only when a reader asked for it was defended above on cost. The objection to
that is better than the defence: *a reader does not know what the architecture holds.* Somebody
typing "will it rain in Pune tomorrow?" is not declining a second opinion — they are asking for the
best answer this workspace can give, and making them know to ask for corroboration is the reader
doing the engine's job.

So **every ordinary forecast turn now retrieves IMD's own forecast alongside the global model**
(`crosscheck.corroborate_with_imd`). Three properties keep it honest:

- **It cannot damage the answer beneath it.** An IMD run that has not published, a point off its
  grid, a window past its 120-hour reach — every failure is a note, never a status. The forecast
  that already stood, stands.
- **It does not turn an answer into a survey.** Where the two agree the reader gets one answer with
  a clause — *"the two broadly agree"* — not the same measure reported twice. Where they differ,
  they are told, because a disagreement between IMD and a global model is information.
- **Nothing is averaged, ranked or voted on.**

And it exposed a real defect that a prompt could not fix. The two sources **did not supply the same
shape**: the global model gives one daily precipitation total, IMD gives eight three-hourly
accumulations. Measured, three runs in a row:

```
S21  Forecast rainfall        7.4 mm      (the whole day)
S16  Precipitation · IMD      0.0 … 2.3   (eight steps, 5.6 mm total)

answer: "IMD's multi-model forecast gives 0.0-7.4 mm"      <- IMD's minimum, GFS's maximum
```

It took one source's floor and the other's ceiling and attributed the span to IMD — a number
attributed to a publisher that did not print it, which is the one error this product must not make.
A direct instruction not to merge ranges across sources **did not stop it**, because the fault was in
the evidence rather than in the reading of it. An accumulation is now summed to the window total the
other source already reports, and the sum says in its own locator that it is a sum. Instantaneous
measures are left per step, because both sources express those as ranges already and the temperature
comparison was correct throughout.

```
S21  Forecast rainfall                          7.4 mm
S16  Precipitation total over the window · IMD  5.6 mm

answer: "IMD's multi-model forecast gives a precipitation total of 5.6 mm for the window,
         while the global model (GFS) gives 7.4 mm; the two broadly agree."
```

**The cost, measured across four ordinary questions: median 12.8 s against a 7–10 s single-source
baseline.** The fetch is not what costs — Mausamgram answers in 0.5 s warm — it is the model weighing
a larger payload. That is the price of the second opinion, and it is one constant
(`corroborate_with_imd`) away from being reverted if a demo needs the seconds back.

## Open

- `imd:subdiv_rainfall_now` (36 subdivisions, Day_1..Day_7) is probed and unconnected — the nearest
  public thing to the blocked S41 district rainfall, at subdivision rather than district resolution.
- `imd:Cyclone_Track_V` exists on the layer list but returned no JSON when asked, consistent with no
  active cyclone. It should be re-probed when one is running, which is the only time it matters.
- The re-retrieval loop is currently one rule — retry the current edition when everything matched a
  superseded one. The general form, where the engine re-plans against a different family or place
  after a thin result, is still not built.
- `evidence_narrative` in `conversation.py` is dead code from the pre-docs/132 continuation design
  and can be deleted.
