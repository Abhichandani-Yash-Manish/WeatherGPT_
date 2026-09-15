# Two gaps the sealed holdout exposed: a misspelt state, and a coast — 15 September 2026

docs/54 recorded a sealed holdout at 8 of 13 declared tasks and named the causes of the misses. Three of
them reduced to two root causes, and this round repairs both. It also states plainly what the repair does
*not* do to the holdout: reading its misses to write that record means the set is now development data.

## What was repaired

| Gap | Where | What it does now |
|---|---|---|
| "Ahmedbad, Gujrat" was refused although the city matched: the misspelt **state** emptied a candidate list | weathergpt_data/gazetteer.py | The state is resolved against the indexed names, bounded to a close and clearly-ahead match, disclosed in the answer, and never swapped for a different state |
| "the Kerala coast" was searched as a settlement and offered twenty villages called Kerla in Rajasthan | weathergpt_data/rule_planner.py, weathergpt_data/dialogue.py, weathergpt_data/warning_tools.py, weathergpt_data/conversation.py | A coast or sea word marks the place as a **sea area**; the resolver leaves it to the tools, and the warning tool asks for a district or a port on that coast instead of attaching guidance to a village |
| "waves **off** Kochi" lost its place entirely, and "in **the** Ahmedabad district" was never read | weathergpt_data/rule_planner.py | 'off' is a place preposition and an article between the preposition and the name is skipped |

Eight checks pin these behaviours in `tests/test_place_typos_and_coasts.py`, over the real gazetteer index and
the real rule planner.

## Measured live, after the repairs

`tmp/evidence-coastal-and-typo.py` against a live local server; the answers are in
`research/implementation/coastal-and-typo-repairs-20260915/`.

- *Will it rain in Ahmedbad, Gujrat tomorrow?* → `needs_selection` with **one** candidate:
  *Ahmedabad, Ahmadābād, State of Gujarāt*, and the note *"State read as State of Gujarāt — the state was read
  as State of Gujarāt in the indexed catalogue, the closest name to Gujrat."* Before the repair the turn
  refused the question outright. It still asks, because an approximate name requires confirmation by design.
- *Are there warnings for the Kerala coast?* → `needs_clarification` with a relevant question: a coast is not a
  district, name a district or a port on it, and the sea-area and coastal bulletins are registered but not
  connected. Before the repair it offered twenty villages.
- *Are there warnings for the Kerala coast and what are the waves off Kochi?* → both halves now ask their own
  specific question rather than sharing a village list: the coast half asks for a district or port, the marine
  half asks which day or window.
- *What are the waves off Kochi for tomorrow?* → `needs_selection` with five candidates, including
  *Kochi, Ernākulam, State of Kerala* - the homonyms are shown rather than one being chosen silently.

## What this does and does not establish

- It establishes that both root causes are repaired, that the repairs are pinned by tests over the real index,
  and that the clarifications a reader now sees are about the question they asked.
- It does **not** raise the sealed holdout's number, and it does not re-run it as a holdout: the misses were
  read to write docs/54 and this record, so `fresh_holdout` is development data from here on. A new
  generalisation number needs a holdout authored after these repairs.
- A single approximate match still requires confirmation rather than being accepted silently. That is a
  deliberate discipline, not an oversight: a wrong district is worse than one question.
- No usability, native-language, mobile or cross-browser acceptance was measured.
