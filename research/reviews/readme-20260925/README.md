# README evidence · 25 September 2026

This record supports the evaluator-facing root README. It is documentation work with selected live browser checks, not a new readiness or scientific validation result. Product code and acceptance registries were not changed.

## What was checked

Read the supplied PS summary, standing product reviews (docs/14, docs/21, docs/72), current hardening and language registries, current frontend record (docs/163), source/refresh records and the current receipt/provider implementations. The final presentation supplied in the workspace establishes the submission identity **Void Pointers, team 118709**; the older README's team 18 is superseded for this submission.

The browser checks used the real workspace at `127.0.0.1:8765`, with a separate automation session. Questions were authored specifically for this task. No model answer was manually replaced, no source response was mocked, and no private conversation database or raw runtime log was exported. Screenshots collapse the conversation rail to exclude unrelated history.

## Recorded conversation

The first three questions were sent in one conversation. The Hindi request followed in that conversation; the Gujarati request was a new conversation.

| Order | Input / selected language | Recorded outcome |
|---|---|---|
| 1 | Will it rain in Pune, Maharashtra tomorrow? / Auto | Pune, rainfall, 26 Sep 00:30–27 Sep 00:30 IST. S21 GFS 0.0 mm; S16 IMD 0.0 mm. |
| 2 | And the day after? / Auto | Retained place, parameter and operation; changed the window to 27 Sep 00:30–28 Sep 00:30 IST. Both sources 0.0 mm. |
| 3 | Actually, I meant Mumbai, Maharashtra. / Auto | Retained rainfall and second window; resolved Mumbai. GFS 0.0 mm; IMD 1.0 mm. Model draft refused; tool wording used and disclosed. |
| 4 | मुंबई, महाराष्ट्र में कल कितनी बारिश होगी? / Hindi | Hindi narrative with source-owned cards. Explicit tomorrow reset the window to 26–27 Sep, 00:30 IST. GFS 0.0 mm; IMD 1.0 mm. |
| 5 | અમદાવાદ, ગુજરાતમાં આવતીકાલે કેટલો વરસાદ પડશે? / Gujarati | Gujarati rendering, with source labels partly English. Ahmedabad, 26–27 Sep, 00:30 IST; both source totals 0.0 mm. |

Reads for the first four outputs are recorded at **25 September 2026, 15:46 IST**; Ahmedabad is **15:48 IST**. These are model forecasts for selected points, not observed rain or district averages. Values and windows are historical capture content, not a claim about weather when this record is read.

Files `01-pune-forecast.txt`, `03-follow-up.txt`, `04-correction.txt`, `05-hindi.txt` and `06-gujarati.txt` contain the visible answer text. `conversation-final.json` contains the first four fully rendered answer bodies, reread from the authored conversation. Text under closed disclosures is not represented as if it was expanded. `02-evidence-receipt.txt` records the opened first receipt. An additional Pune query was used for a clear receipt/dashboard capture; `receipt-capture.txt` records that receipt, which retained the same cached retrieval time and source values.

The first automation reads ran before React had finished changing views/revealing the answer, yielding an incomplete follow-up and an earlier answer under the Hindi filename. These were capture errors, not accepted answer evidence. The final text files were replaced by rereading the completed, saved authored conversation. Screenshots were inspected separately. New-conversation actions subsequently waited for the previous answer to leave the DOM.

## What the examples do not prove

- The opened forecast receipt displays **Evidence: not recorded**, although its owning claim says Model forecast. The README names this limitation and does not alter the screenshot or claim complete metadata.
- The follow-up's prose abbreviates the end date; the claim retains both dates. The README table transcribes the full claim window rather than inventing a calendar-day interpretation.
- The correction's prose uses a 0.0–1.0 mm range; the README lists the two source totals separately, as the source cards do.
- Hindi and Gujarati contain English source labels, retained place names and/or caveats. These captures do not establish fluency, complete localisation or native-speaker acceptance.
- No human microphone capture, real-device push, mobile journey, forecast-skill, load or nationwide acceptance was performed in this documentation task.
- The 19/23 writing and 10/23 speech/recognition figures are the dated language ledger's results, not newly measured service quality. The recorded speech probes used synthesised audio.

## Image provenance

All images in `docs/images/submission/` are browser captures from 25 September 2026. Home, conversation, Hindi, Gujarati and dashboard are actual rendered product views; receipt is an element capture of the opened receipt; warnings shows the dashboard's warning-map section. Viewport sizes were adjusted to make the content readable and keep the fixed composer from obscuring the receipt. Content was not fabricated or retouched. The same-day station reading has no unit in its source and the app says so; the README does not infer one.

`dashboard.txt` preserves the initial dashboard read, including source/time context. The dashboard capture shows Pune selected, the current model reading and forecast-day controls. The warning view keeps its published date. Decorations such as the home skyline and daylight arc are not described as retrieved meteorological evidence.

## Standing finding continuity

- **P01/P02, R03/R04/R10, F05/F08/F11:** receipts, numerical ownership, integrity, temporal support and historical limitations. No universal verification/accuracy claim.
- **P03/P08, R01, F01/F02/F03/F04/F06:** context, corrections, geography, task coverage and specialist/travel boundaries. Three conversational turns are a sample, not generalisation evidence.
- **P04/P07, R09, F07/F09:** document retrieval, agricultural context and unconnected specialist/research products. Nationwide and field acceptance stay open.
- **P06/P10/P11, R02/R06/R07/R08:** warning applicability/delivery, source access and service operation. Local monitoring and push machinery are separate from real-device acceptance.
- **P12/P13/P14/P15, R11/R12, F10:** language, voice/mobile, independent evaluation and honest reporting. No finding or scorecard row was upgraded by this README.

## Documentation checks

- `scripts/check_status_drift.py`: **0 problems**, 1,637 collected Python tests matching the README.
- Relative assets and document links checked for existence; local heading anchors checked against the rendered Markdown.
- GitHub-style Markdown preview inspected for readable tables, images, disclosures and the architecture diagram; desktop and narrow layout checked separately.
- Historical 23 September full-gate counts are attributed to docs/163. The whole product suite was not rerun for a prose/image-only change.

Publication packaging must include the new README images, this evidence directory and the already supplied presentation PDF referenced at the repository root. The final video URL remains unavailable and is stated as pending; no placeholder link is presented as a playable video. This task did not upload the submission or publish the repository.

## Farmer, warning and temperature follow-through

The user correctly noted that the first draft relied too heavily on rainfall examples. Farmer and official-warning journeys were promoted to full sections before the generic conversation tour. Additional questions were sent through the same running app, each in a new conversation:

- `07-farmer.txt`: the latest Ahmedabad cotton advisory with stage/date/advice requested. Returned the **22 September 2026** edition, cotton at squaring/flowering/boll formation, crop passages on physical page 3, weather on page 1 and general context on page 2. The prose calls one fertiliser passage product-label text rather than advice; the README does not convert that qualification into a personal recommendation. `08-farmer-source.txt` preserves the opened source panel.
- `09-warning-broad-result.txt`: “What warning colour has IMD published for Patna, Bihar today, and what hazards does it name?” returned a **Bihar state sweep**, not the requested district-focused answer. This is a scope failure and is retained, not counted as a successful district journey. It took longer than the capture harness's 25-second wait; the result was read after it finished.
- `10-warning-patna.txt`: “What warning colour has IMD published for Patna district today?” returned Patna correctly: orange, heavy rain, thunderstorm/lightning/squall and strong surface winds for 25 September. Source S15, entity `imd-district:364`, bulletin 05:30 IST, retrieved 08:00 IST. The 00:00–00:00 day window is derived from the publisher's day selector. This wording-specific success does not erase the first scope failure.
- `11-hindi-temperature.txt`: “अहमदाबाद, गुजरात में कल अधिकतम तापमान कितना रहेगा?” with Hindi selected returned a Hindi temperature answer and the GFS sample range **25.4–35.9 °C** for **26 Sep 00:30–27 Sep 00:30 IST**, plus separate IMD samples. The screenshot is labelled temperature, not a claim that the engine reduced every model to an independently validated daily maximum.

The farmer and warning captions use source/date context from these outputs. They are historical examples; a reader must retrieve the current applicable bulletin for a real decision. No watch was created and no notification was sent by this documentation task.

The Gujarati farmer candidate (`12-gujarati-farmer.txt`) returned the same edition and preserved English source quotations, but its rendered lead contained malformed passage-count wording (“3 4”) and a literal crop-stage translation. It is retained as a language-quality limitation, not promoted as a fluent farmer-language success. This reinforces the standing native-speaker acceptance gap. The final farmer source-panel capture opens the irrigation passage from this candidate; source S57, edition, district, page and English quotation match the English farmer retrieval.

A Gujarati wind candidate (`14-gujarati-wind.txt`) returned **Partly answered**, with a language-service-unavailable notice and mixed-language tool text. Its GFS evidence retained 10.0–25.3 km/h over 26–27 September, 00:30 IST, while IMD samples retained their own m/s units. This is a recorded downgrade, not a successful Gujarati wind rendering. The README consequently uses the captured Hindi temperature and Gujarati rainfall examples; farmers, warnings, historical analysis and specialist workflows provide the broader product story. Successful showcase selection does not erase the failed candidates.

## Merged README after visual review

The first rewritten README was rejected for removing the original visual and technical strengths. It is preserved as `rejected-readme-v1.md`; the earlier `documentation-checks.json` and preview snapshots describe that draft, not the final merge.

The merged root README retains both original Mermaid blocks byte-for-byte and the original `docs/images/readme/india-warnings.png` byte-for-byte. The map is visible beside the dated Patna example. The original answer pipeline, SQLite evidence-store architecture, source routes and three engineering cases are combined with current home/conversation captures, farmer-source proof, Hindi/Gujarati screenshots, an opened receipt and the dashboard. Lengthy setup and measurement notes are collapsed. Numerical architecture counts are explicitly labelled as the retained 22 September snapshot.

The old atlas prose contradicted its own refusal breakdown and did not match the linked docs/119 run. The merge uses the explicit 20 September docs/119 results inside a disclosure: 256/306 passed outcomes, with 14 upstream, one product-limit and 11 avoidable refusals. It does not claim a newly run benchmark or equate an outcome pass with forecast accuracy. Team identity and hosted-provider disclosures were also corrected.

Final checks: `merged-documentation-checks.json` records 31 existing local references, five valid navigation anchors, both original diagrams preserved and the original map unchanged. A GitHub-style local preview rendered both Mermaid diagrams and all eight embedded images. Desktop (1280 px) and narrow (390 px) checks found no document-level horizontal overflow. Farmer/source, language/receipt and architecture sections were visually inspected. `check_status_drift.py` again reported zero problems, with 1,637 collected Python tests; `git diff --check` passed. This is local rendering verification, not a live GitHub render or publication. The merged preview was opened in the in-app browser.
