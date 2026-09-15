# A misspelt state and a coast: what changed, measured live

Driver: `tmp/evidence-coastal-and-typo.py` against a live local server. This is a desktop-web and engine check, not native-speaker, mobile or cross-browser acceptance.

Repairs: a misspelt state name no longer empties a candidate list the place itself matched, and a coast or sea is read as a region rather than searched for as a settlement. Both were found by the sealed holdout of 15 September 2026 and are recorded as having been informed by it.

## Measured

- **misspelt-state** — Will it rain in Ahmedbad, Gujrat tomorrow?
  - status: needs_selection · facts: 0 · choices offered: 1 · task statuses: ['needs_selection']
  - answer: Which place do you mean? Ahmedabad, Ahmadābād, State of Gujarāt. Choose one, or type its state/district.
  - note: State read as State of Gujarāt — the state was read as State of Gujarāt in the indexed catalogue, the closest name to Gujrat.
- **coast-alone** — Are there warnings for the Kerala coast?
  - status: needs_clarification · facts: 0 · choices offered: 0 · task statuses: ['needs_clarification']
  - answer: A coast or a sea area is not a district, so the official district warning product has nothing to match for Kerala. Name a district or a port on that coast (for example Kochi) and I will read the published guidance for it. The sea-area and coastal bulletins are
- **coast-and-port** — Are there warnings for the Kerala coast and what are the waves off Kochi?
  - status: needs_clarification · facts: 0 · choices offered: 0 · task statuses: ['needs_clarification', 'needs_clarification']
  - answer: Task 1: A coast or a sea area is not a district, so the official district warning product has nothing to match for Kerala. Name a district or a port on that coast (for example Kochi) and I will read the published guidance for it. The sea-area and coastal bulle
- **port-only** — What are the waves off Kochi for tomorrow?
  - status: needs_selection · facts: 0 · choices offered: 5 · task statuses: ['needs_selection']
  - answer: Which place do you mean? Kochi, Yavatmal, State of Mahārāshtra / Kochi, Bhandara, State of Mahārāshtra / Kochi, Chandrapur, State of Mahārāshtra / Kochi, Ernākulam, State of Kerala. Choose one, or type its state/district.

## What this does not establish

- No accuracy claim about place resolution in general: two typo patterns and one coast shape were measured.
- A coast question still asks for a district or a port, because the official district product has nothing to match for a sea area and the sea-area bulletins remain unconnected.
- A single approximate match still asks for confirmation rather than being accepted silently; the answer offers one named candidate instead of twenty.
- No usability, native-language or mobile acceptance was measured.
