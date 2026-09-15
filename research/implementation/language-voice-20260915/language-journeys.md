# Language and voice: the re-measured ledger, three journeys, and real audio

Measured 2026-09-15 UTC on this machine. Ledger: `data/registry/language-support.json`.
Drivers: `tmp/evidence-language-voice.py` against a live local server, and
`python3 scripts/measure_speech_roundtrip.py --languages hi,gu`.
This is a reach and phenomenon measurement. It is not an accuracy, fluency or intelligibility test,
and no native-speaker review of any rendering, transcript or audio has taken place.

## The ledger, re-measured

- **write**: verified for 19 of 23 registered languages: as, bn, brx, doi, en, gu, hi, kn, kok, ks, mai, ml, mr, ne, od, pa, sa, te, ur
- **speak**: verified for 10 of 23 registered languages: bn, en, gu, hi, kn, ml, mr, od, pa, te
- **hear**: verified for 10 of 23 registered languages: bn, en, gu, hi, kn, ml, mr, od, pa, te
  - write failed for mni: the rendering was not written in this script
  - write failed for sat: a protected value did not survive the rendering
  - write failed for sd: the rendering was not written in this script
  - write failed for ta: a protected value was duplicated by the rendering
  - speak failed for as: The language service refused the request (HTTP 400): {"error":{"message":"Please request beta access to as-IN by contacting our support team.","code":"invalid_request_error","reque
  - speak failed for brx: The language service refused the request (HTTP 400): {"error":{"message":"Please request beta access to brx-IN by contacting our support team.","code":"invalid_request_error","requ
  - speak failed for doi: The language service refused the request (HTTP 400): {"error":{"message":"Please request beta access to doi-IN by contacting our support team.","code":"invalid_request_error","requ
  - speak failed for kok: The language service refused the request (HTTP 400): {"error":{"message":"Please request beta access to kok-IN by contacting our support team.","code":"invalid_request_error","requ
  - speak failed for ks: The language service refused the request (HTTP 400): {"error":{"message":"Please request beta access to ks-IN by contacting our support team.","code":"invalid_request_error","reque
  - speak failed for mai: The language service refused the request (HTTP 400): {"error":{"message":"Please request beta access to mai-IN by contacting our support team.","code":"invalid_request_error","requ
  - speak failed for mni: The language service refused the request (HTTP 400): {"error":{"message":"Please request beta access to mni-IN by contacting our support team.","code":"invalid_request_error","requ
  - speak failed for ne: The language service refused the request (HTTP 400): {"error":{"message":"Please request beta access to ne-IN by contacting our support team.","code":"invalid_request_error","reque
  - speak failed for sa: The language service refused the request (HTTP 400): {"error":{"message":"Please request beta access to sa-IN by contacting our support team.","code":"invalid_request_error","reque
  - speak failed for sat: The language service refused the request (HTTP 400): {"error":{"message":"Please request beta access to sat-IN by contacting our support team.","code":"invalid_request_error","requ
  - speak failed for ur: The language service refused the request (HTTP 400): {"error":{"message":"Please request beta access to ur-IN by contacting our support team.","code":"invalid_request_error","reque

## Journeys through the gate

- **hi** — Ahmedabad, Gujarat mein kal subah barish hogi?
  - status: partial · facts: 1 · citations: 2 · choices offered: 0
  - gate: selection None · adherence values_did_not_survive · rendered None
  - answer opens: Ahmedabad · 16 Sep, 09:30–16 Sep, 12:30 IST: Barish ki anumaanit matra: 0.0 mm. Srot: GFS ka poorvanuman; mausam badal sakta hai.
  - note: This answer was not rewritten in the requested language because some of its values did not survive the rendering intact. Showing a partly rewritten answer could change what a number or a warning means
- **gu** — Ahmedabad, Gujarat ma kale savere varsad thashe?
  - status: answered · facts: 1 · citations: 2 · choices offered: 0
  - gate: selection None · adherence written_by_template · rendered None
  - answer opens: પસંદ કરેલા સ્થળ માટે મોડેલની આગાહી: Ahmedabad, Ahmadābād, State of Gujarāt · 2026-09-16 06:30 → 2026-09-16 12:30 IST વરસાદની અંદાજિત માત્રા: 0.0 mm [t1-f1] આ પસ
- **hi** — Aurangabad mein kal barish hogi?
  - status: answered · facts: 24 · citations: 2 · choices offered: 0
  - gate: selection None · adherence rendered_with_protected_values · rendered None
  - answer opens: Aurangabad · 16 Sep, 00:30-17 Sep, 00:30 IST: पूरे समय की कुल अनिर्धारित बारिशः 0.9 mm. अलग-अलग घंटियों में बारिश की मात्रा: 0.0–0.4 mm. स्रोत: Open-Meteo सबसे 
- **ta** — Ahmedabad, Gujarat mein kal barish hogi?
  - status: partial · facts: 2 · citations: 4 · choices offered: 0
  - gate: selection None · adherence rendered_in_another_script · rendered None
  - answer opens: Ahmedabad · 16 Sep, 00:30–17 Sep, 00:30 IST: Barish ki anumaanit matra: 0.0–0.2 mm. Srot: GFS ka poorvanuman; mausam badal sakta hai.
  - note: This answer was not rewritten in the requested language because the rendering came back with characters from another script. A partly rewritten answer could read as the requested language, so the sour
- **hi** — Sultanpur mein kal barish hogi?
  - status: needs_selection · facts: 0 · citations: 0 · choices offered: 20
  - gate: selection user_selected · adherence rendered_with_protected_values · rendered True
  - answer opens: आप किस स्थान की बात कर रहे हैं? Sultānpur, Patna, State of Bihar / Sultānpur, Fazilka, State of Punjab / Sultānpur, Solan, State of Himāchal Pradesh / Sultānpur
- **hi** — Ahmedabad district agromet advisory cotton ke liye kya kehta hai?
  - status: partial · facts: 0 · citations: 1 · choices offered: 0
  - gate: selection None · adherence values_did_not_survive · rendered None
  - answer opens: Ahmedabad, Gujarat: 2026-09-11 ke prakashit bulletin se, fasal cotton ke liye:  Showing 3 of 4 matching source passages; this is a selected extract, not the com
  - note: This answer was not rewritten in the requested language because some of its values did not survive the rendering intact. Showing a partly rewritten answer could change what a number or a warning means

## Real audio, synthesised and transcribed

- **hi** — audio 188204 bytes, model bulbul:v3, detected hi-IN
  - place present: True · number as digits: False · unit present: True · negation present: True
  - transcript: अहमदाबाद में कल पैंतीस मिलीमीटर वर्षा का पूर्वानुमान है, कोई चेतावनी लागू नहीं है।
  - recognition probability: None (the recogniser own number, never answer or forecast confidence)
- **gu** — audio 225836 bytes, model bulbul:v3, detected gu-IN
  - place present: True · number as digits: True · unit present: False · negation present: True
  - transcript: અમદાવાદમાં આવતીકાલે 35 મિલીમીટર વરસાદની આગાહી છે, કોઈ ચેતરણી લાગુ નથી.
  - recognition probability: None (the recogniser own number, never answer or forecast confidence)

## What this does not establish

- No accuracy, intelligibility or fluency: the round trip records what came back, not whether it was right.
- No native-speaker review of any rendering, transcript or audio.
- Reach is per language and per direction and can be withdrawn by the provider: a verified row is what one probe at one instant returned.
- A language whose write failed is shipped in the source language with an honest downgrade rather than an unverified rendering; the Tamil journey above is that behaviour, not a silent fallback.
- The journeys are four turns, not a usability study, and no mobile or screen-reader acceptance was measured.
