# Browser observations — 15 September 2026

Surface: local WeatherGPT at 127.0.0.1:8765, Codex in-app desktop browser. Observed through accessibility state and a screenshot; no mobile or screen-reader acceptance claimed.

## Startup and settings

- Page and navigation loaded, with working place Ahmedabad, Gujarat.
- Initial collection health correctly said no ingestion store existed. After audit requests, local test conversations and ingestion outcomes appeared.
- Settings showed source capabilities, registered-source limits and no configured OpenRouter key.
- Language selector help said no language service key was configured, but offered the previously measured languages.

## Contradictory warning card (approximately 15:01–15:03 IST)

The same visible Ahmedabad card contained:

> No warning in this product

> IMD publishes no warning for this district in this product. That is not an all-clear, and it is not a statement about hazards other products cover.

Its day strip contained:

> 15 SEPT — Today — Thunderstorm/lightning/squall

Tomorrow and later rows showed “No warning in this product.” A screenshot confirmed the headline, quiet paragraph and yellow Today row were visible together. The supplied endpoint exposes warning colour/hazards per day; `web/home.js` instead reads a nonexistent aggregate `data.severity` for the headline. This observation is about the app's rendering of its retrieved product, not a separately issued warning.

## Historical chat and chart

Entered: “Show the annual rainfall trend for Ahmedabad district, Gujarat from 1981 to 2010.”

- Submission completed and rendered a descriptive 54.654 mm/decade slope with 30 input values.
- A rainfall chart and source receipt appeared with source S27, original publication link and page/row locator.
- Expanding “View exact values and evidence IDs” displayed all 30 year/value/evidence rows, from 1981 (880.4 mm, t1-f1) through 2010 (1096.8 mm, t1-f30).
- Copy, print, Markdown, JSON and raw-packet controls were present; actual export/download acceptance was not tested in this browser session.
- Clicking Listen produced the explicit missing language-service key error and no audio. No microphone permission or recording was requested.

## Limits

No exhaustive navigation, export, saved-PDF viewer, keyboard-only, screen-reader, cross-browser, small-screen or rural accessibility evaluation was performed. Component tests are recorded separately and do not replace these missing acceptance checks.
