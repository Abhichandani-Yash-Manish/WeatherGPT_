# A translated answer that does not stall — 15 September 2026

Answering in the reader's language costs real time, and the previous round left it at 27.4 seconds for a
Gujarati district question. Two thirds of that was the answer being translated sentence by sentence —
eleven service calls for one answer, most of them spent on quoted passages. This batch makes the cost
smaller and the fidelity better without moving a single value: **27.4 s → 8.7 s cold, 1.2 s repeated**.

## What changed

**A source quotation is never translated.** A quotation is the document's own words; a rendering puts a
model's paraphrase where the reader expects the source, and in a corpus answer the quotations are the bulk
of the characters. `rendering.quoted_segments` separates the quoted spans from the prose, quotations are
kept verbatim, and the render report counts them (`held_quotations`,
`held_quotation_characters`). An answer that is nothing but a quotation and a page label keeps the previous
behaviour, because it has no prose to render.

**Sentences are rendered through the same gate, concurrently.** The gate is unchanged — every value is
withheld as a sentinel and verified present exactly once afterwards, a rendering that comes back in the
wrong script is refused, and safety-critical clauses are still never translated. What changed is that
independent sentences now go through it in a bounded pool of four, in the order the answer wrote them, so
the wall clock is the slowest call rather than the sum.

**A transient service failure is retried once; a damaged value never is.** A sentence whose protected
values did not survive, or whose rendering came back in another script, is a content failure and is not
retried — the same call would produce the same answer. A service that could not be reached is worth one
more try, because otherwise a single flaky call discards every sentence that did render.

**Repeats are served from a bounded local cache.** The same disclosure lines appear in almost every
answer, and a farmer asking the same question twice is the common case. `speech.translate(..., cache=True)`
stores the rendered text for the masked sentence it came from (sha256 of target, source and the masked
text), under `data/runtime/render-cache`, capped at 2,500 entries with a 30-day expiry, pruned oldest
first. A hit is counted (`speech.cache_hits()`) and returned with `model: local_render_cache`, so a served
rendering is never confused with a fresh call. The query translation is cached the same way.

## Measured after

`research/implementation/render-latency-20260915/runs.json`, reproducible with
`python3 scripts/measure_render_latency.py`. Each question was asked twice in the same process, with the
cache emptied by hand before the run:

| Question | Cold | Repeated | Render adherence |
|---|---|---|---|
| Gujarati, Nashik district agromet, grapes | 8.7 s | 1.2 s | `rendered_with_protected_values` |
| Marathi, Nashik district agromet, grapes | 11.6 s | 7.7 s | `rendered_with_protected_values` |
| Hindi, national bulletin, heavy rainfall | 4.4 s | 1.4 s | `rendered_with_protected_values` |

No rendering was downgraded in any of the six turns: every answer came back in its requested script with
its values intact. The Marathi repeat at 7.7 s is the honest exception: the cache only helps the sentences
that repeat, and a composed answer whose retrieval line or disclosure set changes is rendered again.

The same question through the running product surface (the desktop page's own
/api/chat endpoint, on this machine) answered in **4.3 s cold and 0.1 s repeated**, with
four quotations held back from the translator (1,577 characters) and the note that says a quoted
passage stays in the language it was printed in.

988 Python tests pass, including seven new checks in
`tests/test_rendering_cache_and_quotations.py`: a quotation never reaches the translator, a
quotation-only answer is rendered as before, sentences keep the answer's order, a transient failure is
retried once while a damaged value is not, and the cache is keyed by text, target and source with hits
counted separately.

## What this does not establish

- **Adherence is not quality.** `rendered_with_protected_values` means the script is right and every
  protected value survived; it says nothing about whether the rendering reads well. No fluent or
  native-speaker review of any rendering has taken place.
- **A quotation is served in the document's printed language.** That is deliberate — the reader sees the
  source rather than a paraphrase of it — but a reader who cannot read the document's language still
  cannot read the quotation. The prose around it is what the product translates.
- **Cold answers are still seconds, not instant.** 4–12 s for a first-time translated answer, of which
  about 5 s is retrieval; the translation calls are the rest.
- **The cache holds derived text locally.** It is runtime data under the ignored tree, never published and
  never committed; it holds the masked sentence and its rendering, not a conversation or a user identity.
- One process, one machine, one instant against live sources. No load, browser or device measurement
  follows from these numbers, and no publisher was surveyed.
