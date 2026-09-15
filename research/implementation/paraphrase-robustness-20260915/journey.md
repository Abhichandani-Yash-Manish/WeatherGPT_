# The repaired shapes, live

Drivers: `scripts/measure_paraphrases.py` (38 variants over 11 shapes, all held) and this file, against a live local server. The measurement is a development set and may be tuned on; it measures planner robustness, not answer quality.

## Measured

- **devanagari-rain** — कल अहमदाबाद, गुजरात में सुबह बारिश होगी?
  - status: answered · planner: deterministic_rules · facts: 1 · language adherence: written_by_template
  - answer: Ahmedabad · 16 Sep, 06:30–16 Sep, 12:30 IST: अनुमानित वर्षा की मात्रा: 0.0 mm. स्रोत: GFS पूर्वानुमान; मौसम बदल सकता है।
- **gujarati-rain** — અમદાવાદમાં આવતીકાલે વરસાદ થશે?
  - status: answered · planner: deterministic_rules · facts: 24 · language adherence: rendered_with_protected_values
  - answer: Ahmedabad, Ahmadābād, State of Gujarāt · 2026-09-16 · 00:30 · 2026-09-17 · 00:30 IST કલાક દીઠ વરસાદની માત્રાઃ 0.0–0.0 mm કલાક દીઠ 24 મૂલ્યોમાં. ચોક્કસ તારીખો, સમય, મૂલ્યો અને પુરાવા આઈ.ડી. નીચેનાં કોષ્ટકો અને કોષ્ટકોમાં 
- **station-code** — VOBL ka current weather kya hai?
  - status: answered · planner: deterministic_rules · facts: 2 · language adherence: not_applicable
  - answer: VOBL · Bangaluru Intl: 15 Sep, 11:30 IST par airport ki report: Airport par darj taapmaan: 29 °C. Airport par darj hawa ki raftaar: 4 kt. Ye report airport ki hai, poore shehar ki nahi.
- **agromet-bulletin** — Gujarat state agromet advisory me irrigation ke baare me kya likha hai?
  - status: answered · planner: deterministic_rules · facts: 0 · language adherence: not_applicable
  - answer: Indexed published document:  State composite agromet advisory bulletin · Gujarat · document 22678bac94bc · printed issue 2026-09-12 · 2 day(s) after the printed issue · retrieved 2026-09-14 18:28:49.905251+00:00.  · page
- **tide-out-of-scope** — Kochi me kal tide kya hai?
  - status: unavailable · planner: deterministic_rules · facts: 0 · language adherence: not_applicable
  - answer: The requested research dataset or operation is not connected. Historical rainfall and national temperature analysis are available.
- **crosscheck-hinglish** — Ahmedabad me kal barish ke liye models compare kijiye.
  - status: answered · planner: deterministic_rules · facts: 26 · language adherence: not_applicable
  - answer: Ahmedabad · 16 Sep, 00:30–17 Sep, 00:30 IST: Barish ki anumaanit matra: 0.0–0.4 mm. Srot: GFS ka poorvanuman; mausam badal sakta hai.  Ahmedabad · 16 Sep, 00:30–17 Sep, 00:30 IST: Is poore samay ki kul anumaanit barish: 

## What this does not establish

- The paraphrase set is a development set written by the same hand as the fixes: holding it is not evidence of generalisation (see docs/54 and docs/56 for sealed measurements).
- A plan is not an answer, and no answer here was checked against its source by a human.
- Indic-script support is planned and rendered through the gate, but no native speaker has reviewed any of it, and document coverage in Indian languages remains unmeasured beyond the letterhead count in docs/52.
