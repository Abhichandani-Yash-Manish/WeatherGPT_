# Provider routing on OpenRouter, and the surfaces that reached the frontend

15 September 2026. Follow-up to [the integrated PS assessment](72-integrated-status-and-ps-review.md)
and [the dissemination integration review](73-dissemination-integration-review.md). The user asked for
three things in one batch: merge the open pull request first, route chat and model work through
OpenRouter's free models with the local model kept as the fallback, and make sure every capability the
backend already has is reachable on the desktop frontend.

## 1. The pull request

PR #4 was reviewed and merged; the review, the conflict resolution and the document renumbering are
recorded in [docs/73](73-dissemination-integration-review.md) and in merge commit `268aa20`. The
implementation was already inside main, so the merge changed no behaviour: it recorded the review and
removed the branch's duplicate build report.

## 2. OpenRouter first, the local model as fallback

**The key.** Stored through `python3 scripts/models.py --set-key` in `data/runtime/model-config.json`
at mode 0600. The file is git-ignored, the key is never printed by the script, by the router or by any
report, and no paid model id can be routed: a configured id that does not end in `:free` is refused by
name before any request is built. The key arrived in a chat message, so it has been exposed in a
transcript the workspace does not control; rotating it in the OpenRouter dashboard and re-running
`--set-key` is the safe next step and costs one command.

**The routing order is measured, not assumed.** `python3 scripts/models.py --probe-free` read the live
catalogue on 15 September 2026: 446 models published, 20 of them free, and **none of the twelve ids the
curated ranking named were still published**. Of the twenty free ids, seven declare
`response_format` support, which this client needs because it asks for a strict `json_schema` with
`provider.require_parameters`. The ranking was rebuilt from that measurement — seven ids, all observed
in the workspace's own catalogue read — and the thirteen free ids that cannot serve a strict-JSON
planning turn are recorded in the same registry as not routable by this client, with the reason.

**Two defects were repaired at their cause, both found by running the product.**

- *A body-level failure surrendered the whole provider.* OpenRouter can answer HTTP 200 and put the
  upstream failure in the body. Measured: `{"error": {"message": "Upstream error from Nvidia: Service
  temporarily overloaded", "code": 502}}`. The client reported a generic missing completion and moved
  to the local model without trying the next free id. A body-level failure now belongs to the model:
  the same id is retried once and the order continues, and the upstream message and code are named in
  the final error.
- *The fallback floor named unpublished models.* `providers.DEFAULT_FREE_MODELS` — the ids used only
  when the registry is missing — still listed the previous generation, so a fallback built on them
  would have failed over to the local model every time. It now names observed ids.

**Live measurement.** A real conversation turn through the engine: "Will it rain in Ahmedabad, Gujarat
tomorrow morning?" was planned by the deterministic rules with no model call, then the follow-up
"And what about the evening?" was planned through OpenRouter by
`nvidia/nemotron-3-super-120b-a12b:free` in 21.2 s, needing two attempts because the first hit the
upstream overload above. The validated plan answered from one grounded fact: GFS precipitation for the
evening window, with the source and window attached. `ModelRouter.describe()` reports the order as
`["openrouter", "ollama"]`, and the local service answers with the configured model installed, so the
fallback is real rather than nominal.

Measured again over the served HTTP API with the page token, two turns in one conversation: the first turn was planned by the deterministic rules with no model call, and the follow-up was planned by the same free model in one attempt at 37.9 s, answering with one grounded GFS fact for the evening window (research/reviews/frontend-delivery-20260915/live-chat-turn.json). Free-tier latency varies between runs and both measurements are kept rather than averaged into a number the product does not hold.

**What this does not establish.** Latency is free-tier latency, not a product promise. No end-to-end
acceptance of open-ended conversation quality through a hosted model has been run, no benchmark of
model skill has been taken, and translation and speech still run through the speech service, not through
OpenRouter. Routing a question to OpenRouter is a stated trade: the question text leaves this machine.
Running without a key leaves the rules floor and the local model exactly as before.

## 3. Every declared read-model view is now reachable on the desktop frontend

The audit compared all 26 paths in `product_api.PRODUCT_PATHS` and every workspace route against the
served frontend. Three read-model views had no surface anywhere in the UI — not a panel, not a guided
tool, not a chat shape — and two control paths were unreachable:

| Capability | Before | Now |
|---|---|---|
| `/api/observations/network` | no surface | station network inventory in Observations: one network at a time, 600 km, up to 50 rows, the layer's own station count printed beside the list |
| `/api/radar` | no surface | radar network status board in Observations: the layer reporting on itself, status codes and remarks verbatim |
| `/api/basins` | no surface | national river sub-basin list in Sea and rivers, day fields shown verbatim |
| `/api/push/unsubscribe` | route existed, no control | "Unsubscribe this browser" in the plans & inbox panel, revoking the endpoint the browser actually holds |
| `/api/watches/dma` | route existed, no control | delivery counts per place and per official source, with the statement that a count is not a receipt |

**A served coordinate order was wrong.** The radar view read the GeoJSON pair as
`(latitude, longitude)` while the layer serves `(longitude, latitude)`: all 39 stations were outside
the country as served — Leh arrived as `77.28, 34.28` — and all 39 are inside it once the pair is read
in GeoJSON order, which is how the METAR and AWS readers already read theirs. The parser now reads the
pair as `(longitude, latitude)`, and the live check confirms Leh at `34.28, 77.28`.

**A skipped probe was reported as a failure.** `scripts/start_weather.py --skip-ollama-probe`
printed "no local Ollama was reachable" on a host whose Ollama was answering, because the skipped probe
and the failed probe shared a branch. A skipped probe is now reported as unmeasured.

## 4. Evidence, and what stays open

- Python suite: 1129 tests, with new coverage for the radar coordinate order and the sub-basin day
  fields (`tests/test_national_networks.py`), the body-level provider failover
  (`tests/test_providers.py`), the skipped-probe wording (`tests/test_stakeholder_repairs.py`) and
  the two new control paths plus the three new surfaces in the Node component suites.
- `scripts/verify_all.py`: 26 step(s), 0 failed — Python tests, nine Node component suites, the
  frontend workspace audit and the status drift guard.
- Live turn through the served conversation route: POST /api/chat answered both turns, the follow-up planned by nvidia/nemotron-3-super-120b-a12b:free with one fact attached (research/reviews/frontend-delivery-20260915/live-chat-turn.json).
- Live loopback check, recorded in
  `research/reviews/frontend-delivery-20260915/live-http-checks.json`: a fresh workspace served the
  page token, both changed assets, and all six routes the new controls call — 28 stations listed of 145
  in the layer, 39 of 39 radar stations inside the country, 220 sub-basins of which 212 carry day
  fields, the delivery aggregate and the push state.
- **No DOM or browser rendering was run in this session.** The browser CLI could not launch Chrome
  inside the session sandbox, so the recorded live check is a served-contract check and the rendering
  claims rest on the component suites. This is a limit of the evidence, not an acceptance.
- Still open, unchanged: live changed-edition device delivery, warning origin authentication, mobile
  and rural journeys, native-language and noisy-audio review, sustained service operation, and any
  claim that a hosted free model answers as well as a measured product needs.
