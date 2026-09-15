# Historical alias candidates: offered, never substituted — 15 September 2026

[The gap register](31-full-solution-gap-register.md) recorded **G10** from docs/21 A04: Mysuru district history found no series, the source spelling "Mysore" worked, and a city-named historical lookup asked for a district without resolving it. The missing piece was a dated, reviewed crosswalk, which this project does not have. What it does have is a source-lined place index (S61) and the publisher's own historical spellings. This batch connects them as **candidates that require confirmation**, so nothing is substituted silently.

## What changed

When a historical district lookup finds no series, research_answers.alias_candidates now looks for candidates in the place index and offers them as choices:

- **A place alternate name that matches a publisher series label.** Mysuru's place record carries "Mysore" as another name, and the S27 table spells the district "Mysore". The candidate is labelled with that basis.
- **The district a settlement falls in.** Bhubaneswar's place record places it in Khordha district, and the publisher's older spelling "Khurda" is an alternate name of the district place itself. Both the district name and its alternates are checked against the series index.
- **State spellings are matched with the publisher's historical labels** (Odisha to Orissa), because the S27 table keeps the historical state name.

A candidate is used only after the user chooses it (button or text). Choosing rewrites only the place of the history task, records a place edit, and re-runs the lookup against the publisher series. A name with no candidate keeps the existing refusal, word for word: "I will not substitute national or nearby-district data." The candidate label always states that it is a place-index label, not a reviewed LGD crosswalk.

## Recorded live evidence

[research/implementation/historical-alias-20260915](../research/implementation/historical-alias-20260915/), local model on this machine:

| Journey | Turn 1 | Turn 2 |
|---|---|---|
| A1: "annual rainfall in Mysuru district, Karnataka in 2010" | needs_selection — candidate "Mysore district series, Karnataka (S27) — the place index places Mysuru in Mysore district" | chose it to **answered**, one published 2010 value |
| A2: "annual rainfall in Bhubaneswar, Odisha in 2010" | needs_selection — candidate "Khurda district series, Orissa (S27)" from the district place's alternate spelling | chose it to **answered**, one published 2010 value |
| A3: "annual rainfall in Nowhere district, Karnataka in 2010" | unavailable with the refusal text; no candidate offered | — |

**625 automated tests pass**, including six new alias checks: alternate-name candidate, city-to-district candidate, district older-spelling candidate, no-candidate refusal, cap and de-duplication, and the confirmation rewrite touching only the place.

## What this does not establish

- **No reviewed dated crosswalk.** GeoNames source labels are not authoritative LGD codes, boundaries or a reviewed rename history. The candidate is a lead the user confirms, not a mapping the project asserts.
- **No automatic alias resolution.** A question that does not confirm a candidate still receives the source-name refusal.
- **No nationwide alias coverage measurement.** The candidates come from whatever the place index records for the asked name; unknown coverage is not claimed.
- **The remaining external need is unchanged:** a dated administrative crosswalk with boundary edge cases would still be the right source for automatic resolution (G10's blocked half).
