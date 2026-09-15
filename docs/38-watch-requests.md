# Watch requests: registered, checked on demand, never faked — 15 September 2026

[The gap register](31-full-solution-gap-register.md) recorded **G11** from docs/21 A05: "Notify me if an official flood warning is issued for Patna tonight" became a one-time warning lookup. No fabricated confirmation occurred, but the requested action was not handled either. This batch handles the request half honestly: a local watch is registered, named with its place, hazard and window, checked only when it is asked to be, and a hazard the connected official products do not carry is recorded as not connected rather than mapped onto a similar-sounding product.

## What changed

- **A local watch store**, weathergpt_data/watches.py, records each request with its place, hazard, window, created time and state in a runtime SQLite store. States are explicit: registered_check_on_request, checked_no_match, matched, hazard_not_connected, expired.
- **Intent is recognised deterministically** ("notify/alert/inform/tell/warn me ... if/when"), and the hazard is read from the user's own words. Flood and cyclone are on a declared not-connected list: the connected official products are the IMD district warning product and the CAP relay, and neither carries them.
- **Evaluation is pure and bounded.** A match requires a current, non-quiet district-warning day whose own hazard codes intersect the watch hazard; codes are the layer's own (heavy rain 2/16/17, thunderstorm 4, strong winds 8, from docs/27). An unlisted code is reported as unmapped, never matched.
- **Registration hangs off the normal warning turn.** After a warning task executes, a recognised watch request stores the resolved place and the window the plan used, and the answer states plainly: no push, no background delivery, a no-match is not an all-clear, origin authentication remains unverified.
- **A planner fallback keeps the request from being lost.** If the planner cannot preserve a watch question, a bounded compiler extracts a place written as "for/in <name>, <state>" and builds one warning task with the question verbatim. The warning tool still owns place resolution and ambiguity.
- **Surfaces.** POST /api/watches/check (one watch or all open), GET /api/watches, scripts/check_watches.py for a foreground run, and the Watch panel now reads the inbox and offers Check now instead of the old placeholder refusal.

## Recorded live evidence

[research/implementation/watches-20260915](../research/implementation/watches-20260915/), local engine on this machine:

| Journey | Registered | Checked |
|---|---|---|
| W1: "Notify me if an official flood warning is issued for Guwahati, Assam tonight" | place Guwahati, hazard flood, window tonight 18:30-22:30 IST, state registered_check_on_request | hazard_not_connected: the connected products do not carry a flood warning, and it was not mapped onto a similar product |
| W2: "Notify me if a heavy rain warning is issued for Thiruvananthapuram, Kerala tomorrow" | place Thiruvananthapuram, hazard heavy_rain | checked_no_match: no current official district day matches; the recorded detail says this is not an all-clear |

The store also holds duplicate watches from a first run that failed while writing its report; they are preserved rather than cleaned, which is why the foreground check reported four watches for two journeys.

**627 automated tests pass** (ten watch checks), and the suite component test now asserts the panel reads the inbox, names a watch place, and calls the check route only when Check now is pressed. No test reaches the network or the model.

## What this does not establish

- **No delivery.** There is no push, email, background daemon or subscription service, and none is claimed. A watch is evaluated only when the user asks or the route is called.
- **No origin authentication or applicability change.** The warning tool's own limits stand: origin unverified, no all-clear, CAP lifecycle never authorises dissemination.
- **No flood or cyclone coverage.** Those watches are recorded as not connected; the required source products are still missing (G11's delivery half and G12's specialist half).
- **The hazard-code mapping is observed, not universal.** Only codes seen in the district warning layer are mapped; others are reported unmapped.
- **Foreground checks are current-clock.** A check that runs while a source is stale records that state; it does not prove the watch was continuously evaluated.
