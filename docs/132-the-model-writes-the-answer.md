# 132 — The model writes the answer

*21 September 2026.*

The complaint was that the chat had no conversational flow, that the answers were framed by the
machine rather than for the reader, and that this was the weakest part of the product. It was right,
and the measurement is simple enough to repeat: eleven questions across eleven intents, asked of the
live engine, and a count of how many answers a model had written.

    before:  1 of 11
    after:   6 of 11 on the first pass, 8 of 11 once the checks were corrected

The other ten had been written by templates.

## What the model's job used to be

A continuation. The system prompt said it plainly:

> The answer's first sentence is already written and is supplied as opening_sentence: it is not
> yours to rewrite, repeat or contradict. Write ONLY the sentence or two that follow it.

So the shape of every answer was the template's, and the model furnished it. A reader met the
machine's sentence first and their own answer second, if at all.

Two mechanisms kept that in place, and both were invisible until measured.

**The intent allowlist had eight entries.** The six it left out — history, warning, agriculture,
document, climate, comparison — are exactly the answers a reader is most likely to find stiff. A
warning and an agricultural advisory could never be written for a reader, by construction.

**The gate required the floor to be under 600 characters and four newlines.** That is backwards. A
long, table-shaped deterministic answer is precisely where prose helps most, so the richest answers
were the ones guaranteed to stay templated.

## What it is now

The model is given the evidence and the question, and writes the reply. The tool-owned opening is
still supplied — as something true it may use, not as a prefix it must keep — so nothing the tools
state is lost, and the deterministic text remains the floor underneath.

    Yes — two districts in Kerala carry a hazard colour in the current IMD district bulletin …

    Pune's total precipitation for 2019 was 1758.6 mm, summed across …

    I can check tomorrow's weather for you, but I need to know the place first. Also, "bad" isn't
    something I can measure directly — tell me what you care about: rain, wind, heat, or any
    official warning?

The last of those is a clarification, which had been "Which city or village should I check?" — a
form rejecting a field.

## What keeps this safe is not the gate

It is the check that runs on what the model wrote, against the evidence it was given. Every number
must come from that evidence. Every unit must match its source. The place must be named. An invented
link or certainty is refused. The language must be the one asked for. When any of it fails, the
deterministic floor stands and the reason is recorded on the turn.

Three rules are new, and each replaces something a rewrite could otherwise have dropped silently:

- **A published passage is the publisher's own words.** One the model *cites* must appear verbatim,
  and a turn whose evidence is a bulletin must cite one or keep the floor. A passage it did not cite
  is a selection — the model judged it did not answer the question — and stays in the evidence list
  rather than being dumped into the prose.
- **Safety clauses are held.** The sentence saying an absence of official guidance is not an
  all-clear; the one saying a warning reading is not an instruction; the shared-lineage caveat that
  stops two sources agreeing from reading as confirmation; an incomplete bulletin context; a year the
  source could not supply. A held clause the prose dropped is put back.
- **The measurement check applies only where a measurement was retrieved.** It was refusing every
  cotton advisory over "acephate 75 % SP" — a pesticide concentration printed in the publisher's own
  bulletin, policed as though it were a rainfall figure.

## The mistake worth remembering

Widening what the model is GIVEN without widening what the check ALLOWS refused most turns at first,
and each refusal named something this product had handed it moments earlier: a total it had
computed, a distance out of its own place label, a figure printed in the bulletin it supplied, an
evidence id belonging to a passage rather than a fact.

The fix was structural rather than a list of exceptions. The composer's payload travels back with
the answer, and the check reads that same payload. They cannot drift apart again, because there is
now one definition of "what the model was shown".

A second instance of the same error: an observation fact is placed at its station and its label
reads `MUMBAI · 2.32 km from the requested point`. The place check split it on a comma, so the whole
string became the thing the prose had to contain — and an answer opening "At Mumbai" was refused for
not naming Mumbai.

## What it does not do

It does not decide what to retrieve — the planner already did that, and already used a model. It does
not compute a value, round one, convert a unit or choose a window. It does not make a claim the
evidence does not carry: asked whether the air is safe for an asthmatic child, it declines the
medical judgement, reports the index and the concentrations, and closes by saying they are modelled
values for a grid cell rather than a reading from a ground monitor.

And it does not replace the deterministic renderers. They still run, their text is kept on every turn
as `tool_answer`, and it is what a reader gets whenever the check above says the prose may not stand.
