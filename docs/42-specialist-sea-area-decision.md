# Specialist sea-area and coastal identity: the recorded decision — 15 September 2026

[The gap register](31-full-solution-gap-register.md) lists **G12**: the marine tool returns modeled wave cells within 50 km and refuses to name a sea area, and the official S58/S59 bulletins were ingested but not conversational. The corpus batch made their **text** reachable as published documents. Named sea-area identity, validity windows and a domain-reviewed specialist composition remain unresolved. This document records why that half is not closed locally.

## What is now reachable

- A conversation can retrieve the indexed sea-area and coastal bulletin passages with their family, scope, printed issue date, currency, retrieval instant, physical page and document identity attached, warning-classified text separated as reference only (docs/32).
- The marine tool still returns modeled wave height/direction/period at the answering grid cell with its distance, and still says what it is not: no named sea-area identity, no official bulletin product, no navigation or fishing clearance.

## Why identity is not added here

- The bulletins are published as free text; a named sea area (for example "North Maharashtra coast") is not a key the index carries, and the publisher's extraction is reading-order unverified. Mapping a coastal place to a named sea area would be an invented crosswalk.
- Current validity lives in printed wording such as "Bulletin Valid for 12 hrs from 21 UTC ... to 09 UTC"; the family extraction rules do not carry that field, and publications are immutable by content hash, so adding a field requires a new extraction version and a re-ingest — not a silent edit of an existing publication.
- A domain review of marine wording and applicability has not taken place, and the project's own rule forbids implying one from a prototype parse.

## Decision and next action

Keep the limitation explicit: no sea-area identity claim is made, the corpus text remains available and labelled as published document text, and G12 stays open with these exact inputs needed: a new reviewed extraction version that carries printed validity and a sea-area label where the publisher states one, plus a marine domain review. Nothing is mapped in the meantime.
