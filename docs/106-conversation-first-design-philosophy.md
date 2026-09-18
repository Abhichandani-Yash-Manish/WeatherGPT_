# 104 — The conversation is the product: the design philosophy, and the front door

18 September 2026. This is a design-philosophy change and the first batch that carries it out. It replaces
the governing idea in [DESIGN.md](../DESIGN.md) — *"a field instrument, not a dashboard"* — and it exists
because the instrument framing, executed faithfully, produced a workspace that reads as a laboratory record
rather than a product. The engine, the provenance discipline and the refusals are not in question here and
nothing in this batch weakens one of them.

## 1. What was wrong, as the running build showed it

Measured against this machine on port 8791, 18 September, before any change in this batch:

| Surface | What it led with |
| --- | --- |
| The front door | the product's name, a paragraph of method, and a panel titled **"the shape of an answer"** — a table of *words where values would go*, captioned "This page prints no measurement it did not read from this machine". A weather product's first screen showed no weather. |
| Ask | a banner explaining what a pinned place is (none were pinned), a "reading register" offering Brief / Conversational / Full evidence, and five stored conversations each carrying a **Delete from this machine** button in hazard red — a destructive action at the same visual weight as the content, in a colour [DESIGN.md](../DESIGN.md) reserves for published hazards. |
| Today | four counters — *districts in this read*, *district-days with a published colour*, *editions behind the newest in this read*, *radar stations reporting a status*. Facts about the pipeline, not about the weather. |

The common cause is one sentence: **the interface was written from the machine's point of view.** Every
label named the system's act — a read, an edition, a register, a locator — rather than the reader's
question. The rigour was real and was pointed at the reader instead of held underneath them.

## 2. The philosophy that replaces it

**The conversation is the product.** One way in, and the apparatus is reachable rather than compulsory.

1. **Answer first, apparatus on demand.** Nothing precedes the answer. Every disclosure attaches to the
   value it qualifies instead of standing in front of it. Never absent, never first.
2. **Speak from the reader's position.** "Districts in this read" is the machine's sentence; the reader's
   is "where is it dangerous today". The precise term survives as the expert label underneath, not as the
   headline.
3. **Depth is earned, not dumped.** Nineteen peer surfaces in a rail is a survey of the architecture. They
   become depth that an answer unfolds, which is also how the architecture gets *highlighted* rather than
   merely present.
4. **Spend boldness once per surface**, on the reading itself.

### Two voices, and they are typographic

The product's central claim is that a model plans and writes while a governed tool owns every value. That
is now visible rather than described:

- **Tiro Devanagari Hindi** is the human voice — prose, the written sentence, the invitation. It was drawn
  for Indian scripts and carries Latin and Devanagari on one set of proportions, which matters in a product
  that answers in Hindi as readily as in English.
- **IBM Plex Mono** is the machine voice — every value, unit, locator, timestamp and source id.
- **IBM Plex Sans** is the interface voice — controls and labels, which are neither.

If a number ever appears in the human face, that is a defect worth seeing.

Every face is self-hosted and bundled (`src/styles/fonts.ts`): the workspace serves under
`default-src 'self'`, so a Google Fonts stylesheet or a CDN face cannot load here at all. The six
script-specific faces (Bangla, Tamil, Telugu, Kannada, Gujarati) load **on demand** — a reader who never
asks for Tamil does not pay for a Tamil face. Loading a face is not a claim that the product can write the
language: that remains the engine's adherence gate, measured per direction.

### Colour

The four IMD hazard colours are untouched and still reached only through a published colour. The single
accent is **indigo** (`#2c3e8f` light, `#8ea2ef` dark), chosen because it sits far from all four hazard
hues in both themes, so an accent can never be mistaken for a warning level. The ground is a cool paper
rather than a warm cream, because everything this product reads is a printed bulletin and monsoon light is
blue.

The design layer is scoped to `.v3` (`src/styles/voices.css`). The reframe moves surface by surface and a
half-applied palette is worse than either palette, so these tokens override nothing until a surface opts
in. When the last surface has moved, the scope disappears.

## 3. What landed: the front door

`src/landing/FrontDoor.tsx` replaces `Landing.tsx` at an empty address. It opens on **the country's
weather as this machine read it**, then offers the question box, then states its provenance.

The live reading on this machine, 18 September 17:09 IST:

> **No district is under an orange or red warning today.**
> 298 carry a yellow caution, and 445 have nothing flagged.
> `IMD district warning bulletin, 15 Sep edition, 756 districts · read 17:09 IST`
> 14 of those districts are still publishing an older edition than the newest this read returned, so their
> day above is what that older edition printed.

### The backend change this required, and the trap it avoids

The overview read stated a five-day `tally` and no per-day column, so a front door had nothing honest to
lead with. `product_api.today_tally()` adds the column covering today.

It is deliberately **not** the existing `tally`, and the reason is a live measurement: on 18 September the
national read carried **one red and 26 orange district-days, and every one of them was in the past**. The
column covering today held only green and yellow. A front door reaching for the five-day tally would have
announced a hazard that is over. Two further distinctions the new tally keeps:

- A **quiet** day is dropped by `tally` but counted here: a quiet green is the source saying green for
  today, and a reader asking about today is entitled to that answer.
- A district whose table has **no day covering today** is counted (`districts_with_no_day_covering_today`),
  not silently lost.

### The honesty rule the page enforces

An **absent** `today` block is not a quiet day. A server that has not been restarted since this field was
added returns an overview without it, and printing `0` there would state that no district carries a
caution — a number no read produced. This was reproduced during the batch: the first build printed
"0 carry a yellow caution, and 0 have nothing flagged" against a server still running the old code. The
page now tests the block's presence, never its truthiness, and a read that does not state today says so
and prints no edition line either.

## 4. Evidence

| Check | Result |
| --- | --- |
| `tests/test_today_tally.py` | 5 checks: today's column against a past red, a quiet green, a district with no day covering today, an uncoloured day, and no rows |
| `frontend/src/landing/frontdoor.test.tsx` | 8 checks, including the past-severity trap, the absent-block rule and the failed read |
| `frontend/src/a11y/a11y.test.tsx` | the front door scans clean under axe-core; the superseded landing page stays under the gate until the shell reframe removes it |
| `python3 -m pytest tests/ -q` | **1356 passed** (1351 before this batch) |
| `frontend`: `npx tsc --noEmit`, `npx vitest run` | clean; **62 suites, 348 checks** (61 and 340 before) |
| Captures | desktop 1440×900, phone 390×844 and dark at 1440×900, against the live read on loopback |

## 5. Two defects found while measuring, not yet repaired

Recorded here so they are not lost; neither is touched by this batch.

1. **An unknown deep link renders Ask and says nothing.** `#/today` is not a route — the id is `overview` —
   and `useHashRoute.ts:18` falls back to the assistant view silently. docs/92 §4c made the opposite
   promise for assets, that a stale bookmark "fails in words instead of fetching a deleted script". The
   same promise is not kept for routes.
2. **Seven built routes no UI calls.** `/api/radar`, `/api/basins`, `/api/answer`, `/api/briefing/run`,
   `/api/plans/replay`, `/api/plans/update` and `/api/warm` are reachable and never requested by
   `frontend/src`. `docs/BACKEND_FEATURE_INVENTORY.md` states that Observations reads `/api/radar` and
   that Sea and rivers reads `/api/basins`; measured against the React tree, neither does. The inventory
   describes an intent, not the served build.

## 6. What this does not claim

It does not claim the reframe is done: Ask, the shell rail and the eighteen module surfaces are unchanged
and still carry the instrument language. It does not claim any PS feature state moves — no engine, adapter,
route contract or evidence rule changed except the added `today` block. It does not claim a design is
validated: no reader other than this machine's owner has used the new front door, and a capture is one
render on one machine on one day. `Landing.tsx` is still in the tree, unserved.
