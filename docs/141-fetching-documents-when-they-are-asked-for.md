# 141 — Fetching documents when they are asked for

> **The proposal.** Rather than ingesting documents ahead of time, fetch them when a question needs
> them. It would be slower and less efficient, but the workspace would have the maximum possible data
> available, and it should not hesitate to fetch and decode where it can.
>
> **The verdict.** The instinct is right and identifies the product's weakest measured area. The
> mechanism, applied to ordinary turns, would damage three things this project has spent its whole life
> protecting. There is a narrower version that gets most of the benefit and costs none of them, and it
> is what this document recommends.

Written 22 September 2026, against a corpus of **661 documents and 8,286 passages**.

---

## A correction, first

An earlier version of this document said the corpus held agromet bulletins for about five per cent of
India's districts, and recommended widening the daily sweep on that basis. **That was wrong, and the
change it justified has been reverted.**

The daily job passes `--district-limit 40`. I read that as total coverage. It is a RATE: how many
queued targets each run takes, accumulating across runs. Measured against the index rather than
inferred from a flag:

| | |
|---|---|
| Documents held | 661 |
| Passages held | 8,286 |
| **Distinct regions with district agromet passages** | **571** |

Three quarters of the country, not five per cent. And the decisive number, from the same day's atlas
run: of the **sixteen** agromet and advisory failures, the count whose answer says the bulletin is not
held is **zero**.

So the weak group is not a coverage gap, and "have more data at hand" — however reasonable it sounds —
would not have moved it. What the failures actually are, read one by one:

| what happened | how many |
|---|---|
| A good answer scored `partial` — Rajkot's cotton advisory quoted correctly, Ujjain's "no rain, 0.0 mm over both days" | 6 |
| The engine asked for a detail it could have inferred — one demanded an exact bulletin **date**; another asked which district, for a question naming Davangere | 5 |
| Raw document metadata printed where prose belongs — *"Indexed published document: … document f558090eb98b"*, and an edition **diff** returned instead of the advisory | 2 |
| Routed to conversation instead of retrieval | 3 |

None of those is fixed by fetching more. Two of them are fixed by the engine asking less and printing
better, which is the same intelligence-layer work as the rest of the chat repairs.

## Why fetching at question time is the wrong mechanism

### 1. It fails exactly when it matters

A turn already takes 8–20 seconds. A live PDF fetch and extraction adds somewhere between 5 and 30
more, and that is on a good day. On a bad day — a cyclone, when the publisher's site is saturated and
everybody in the country is asking it the same question — the fetch is slow or fails.

A pre-ingested corpus answers on a bad day: *"this is what was published at 11:30 today."* A lazy-fetch
product goes quiet at the exact moment a disaster-management tool has to work. That is the wrong
failure mode for this problem statement, and it is not a tuning issue.

### 2. It cannot honour the extraction rules this product already has

`bulletin_context.parent_context` refuses outright when a document's family is not one whose layout has
been reviewed:

```python
if document['family'] not in {'arnej_grid', 'tnau_grid', 'gkms_grid'}:
    raise SourceError('Parent context layout has not been reviewed')
```

That rule is not bureaucracy. A bulletin is a grid of crops against advice, and reading it with the
wrong layout assumption does not fail loudly — it silently attributes one crop's advice to another. The
product is built so that cannot happen.

A document fetched at question time has not been layout-reviewed, by definition. So lazy fetching has
two options and both are bad: bypass the rule, and start quoting advice extracted from a structure
nobody checked; or honour it, and refuse most of what it fetches, having spent thirty seconds first.

### 3. It weakens the one claim the whole product rests on

Every number here carries where it came from and when it was read. Behind that, ingestion verifies a
hash, pins an extraction version, and records what it could not read. That is why the README can say an
answer stating an unsupported figure is rejected rather than softened.

"Fetched just now, extracted with an unreviewed layout, quoted to you" is a materially weaker claim than
anything else this workspace makes. Mixing it into ordinary answers, invisibly, would mean the
provenance line no longer means one thing.

---

## What to do instead

### ~~Widen the scheduled refresh~~ — withdrawn

This was the first recommendation and it rested on the miscount corrected above. With 571 regions
already held and no failure caused by a missing document, tripling the request rate against a public
publisher buys nothing measurable. Reverted.

The measurement that supported it is kept below, because the *cost* figures are real and are the
argument against fetching at question time.

That single line is the agromet coverage gap. It is not a reasoning failure and no amount of work on
the intelligence layer will touch it — the corpus holds bulletins for about five per cent of the
country's districts, so the other ninety-five per cent can only be answered with "not held here".

And it is cheap to fix. From the last real run, measured rather than estimated:

| | |
|---|---|
| Whole refresh, end to end | **3 m 23 s** |
| Document families step | 93.7 s |
| District sweep, 40 districts | **99.5 s** — about 2.5 s per district |

So the sweep scales at roughly two and a half seconds a district on a job that runs unattended, twice a
day, while nobody is waiting:

| districts per run | sweep time |
|---|---|
| 40 (today) | 1.7 min |
| 120 | 5 min |
| 240 | 10 min |
| 756 (everything) | ~31 min |

A background job can afford thirty minutes. A reader waiting for an answer cannot afford thirty
seconds. That asymmetry is the whole argument: **the same work, moved off the question and onto the
schedule, costs nothing a reader experiences and buys the coverage the proposal is asking for.**

The sweep takes queued targets, so coverage already grows run by run; raising the limit is the
difference between covering the country in weeks and covering it tonight. The honest caveat is that
this depends on the publisher tolerating the request rate, which is worth watching on the first widened
run rather than assuming in either direction.

### Say precisely what is missing, and queue it

When a question needs a document the corpus lacks, the answer should name the gap — district, family,
and that it was not held at this read — and the request should be recorded so the next scheduled run
fetches it. Coverage then grows from real demand instead of a guess about which districts matter.

That is a small, safe, high-value change and it should be done first.

### A bounded, consented live fetch — the narrow version worth building

Where the reader explicitly asks for **one named published document** that the corpus does not hold,
offer it as an action rather than doing it silently:

> This bulletin is not held here. **Fetch it now** — about 30 seconds, and it will be read with an
> unreviewed layout, so anything quoted from it says so.

This keeps every property that matters:

| | |
|---|---|
| Ordinary turns stay fast | nothing changes unless the reader presses it |
| Consent is explicit | the reader chose to wait and to accept weaker provenance |
| The weaker claim is disclosed | the answer says the layout was unreviewed, in the answer |
| The failure mode is honest | a fetch that fails says so; nothing is invented |
| Coverage grows | what was fetched once is queued for proper ingestion |

The key design point is that the fetched document is marked as a **different kind of evidence** — not
folded in beside hash-verified, layout-reviewed passages as though it were the same thing.

---

## Recommendation, in order

1. **Stop the engine asking for what it can infer.** Five of the sixteen failures are the engine
   demanding a bulletin date or a district the question already named. This is the largest real gain
   and it is intelligence-layer work, not ingestion work.
2. **Print prose, not document metadata.** Two failures return an index record or an edition diff
   where an advisory belongs.
3. **Name the gap and queue the request** when a document genuinely is missing. Still worth doing —
   it just turns out not to be the current bottleneck.
4. **Then** the consented single-document fetch, if anything is left that justifies the complexity.

What I would not do is make ordinary turns fetch documents. It trades a fast, verified, honest answer
for a slow one with a weaker claim, and it does it at the moment the product is most needed.
