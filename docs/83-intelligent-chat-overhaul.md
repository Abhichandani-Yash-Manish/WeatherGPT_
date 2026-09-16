# Intelligent chat overhaul: the model owns the conversation, the tools own the facts

> Current requirement-by-requirement reading after this batch: [docs/84](84-ps-progress-and-pictures.md).

16 September 2026. The instruction that set this batch: make the chat the core feature, make it seamless and
flexible - it should decide **when to retrieve** and when to simply answer ("hello", a thank-you, a capability
question, a piece of logic) - and make sure a **real LLM call is made**, with no silent hardcoded or scripted
stand-in deciding a turn. Multilingual chat (PS feature 6) and the voice path (feature 8) are the focus, and the
architecture underneath is to be hardened rather than replaced.

## Measured before designing (16 September 2026, live providers)

Two turns through the real engine with the real provider chain (no planner-policy switch existed yet):

- **"hello" failed outright.** SourceError: "Question interpretation did not preserve the requested tasks:
  Every task request_quote must copy its supporting clause exactly from the current question". A greeting has
  no task to quote, so the whole turn died. There is no conversational path at all today.
- **"what can you do?" took 28.9 s** and was answered by nvidia/nemotron-3-super-120b-a12b:free as a general
  explanation written from the **model own memory of itself** - vague, and partly wrong about this workspace
  (it does hold station observations and district warnings; the source ledger knows exactly which products are
  connected and which are blocked).

So the gap is not a nicer reply. It is: no conversational intent, capability questions answered from memory
instead of from the workspace own registries, and a planner that silently uses a rules floor and then dies when
the model plan does not validate.

## The architecture decision

**The model owns the conversation; the tools own the facts.** Concretely:

| Layer | Owner | Rule |
| --- | --- | --- |
| Understanding, deciding to retrieve or not, choosing tools, wording, language | the LLM | never decides a value |
| Every number, unit, date, window, place, source identifier, warning state | the governed tools | never written by the model |
| Validating a model-written sentence against those facts, and the floor when validation fails | deterministic code | never a silent substitute |

"No hardcoded fallback" therefore means: no scripted path decides *what the answer is*. Two bounded floors stay,
and both are visible to the reader and recorded in the trace:

1. when a model-written sentence fails the deterministic checks, the tool-owned fact renderer states the facts,
   and the trace records why the prose was refused;
2. the deterministic rule planner remains only as an **explicit offline mode** (WEATHERGPT_PLANNER=rules,
   recorded in the trace) and behind the already-labelled **first reading** preview, which is a reading and
   never an answer.

## Stage A1 - the planner is the model

- ModelRouter.plan becomes **model-first**: the provider chain plans every turn; the rules seed is no longer
  silently preferred. A rules plan is used only when the policy says so.
- A new policy, WEATHERGPT_PLANNER=model|rules (default model), is recorded in trace.planning.planner_policy,
  so "which planner answered this turn" is never inferred.
- A provider outage raises an honest error naming every provider tried. It does not quietly answer from rules.
- A plan that fails validation is **repaired with the validator own message** (the existing repair attempt), and
  if it still fails the turn degrades gracefully - a status, a note and the validator message in the trace -
  instead of raising at the reader.

## Stage A2 - conversational turns (the headline)

- New intent chat, with an empty task list allowed **only** for it and a plan field chat: {kind}, where kind is
  one of greeting, thanks, capability, meta, logic, small_talk, out_of_scope.
- The engine composes the reply with the **same generation path** evidence answers use, so the language tier,
  the answer budget and the validation machinery are shared. The composition prompt receives deterministic
  context only: the clock, the tool catalogue, the source ledger counts (connected / wired to chat / blocked),
  what the conversation already established, and which provider is answering.
- **Nothing may be invented**: the composed chat text is rejected if it contains a digit, a measurement unit, a
  date-like token, a place it was not given, a warning word, a source identifier or a URL. One repair attempt is
  made with the violation named; if it still fails, the turn says plainly that a conversational reply could not
  be written without unsupported claims, and the reason is recorded.
- A chat turn retrieves nothing, writes no fact and cites nothing: status conversation, empty facts and
  citations, and a standing note that it is a conversational reply and not retrieved evidence.
- Chat is **multilingual**: the reply is written in the question language and then verified by the existing
  answer-language tier, so a rendering whose script or protected values do not survive is downgraded exactly as
  an evidence answer is.

## Stage A3 - evidence answers get a written sentence, facts stay tool-owned

Today a turn with facts is rendered by claims.render_facts and the model never writes the answer. The overhaul
lets the model write a short narrative answer **from the same facts**, behind the checks that already exist for
fact-free turns (tool-number subset, measurement-unit match, evidence identifiers, no links, no certainty
claims), extended with the protected identities (places, districts, regions) and the requested language. On any
failure the tool-owned renderer states the facts, and trace.generation records the refusal. Disclaimer and limit
lines stay tool-owned text on the card, never rewritten by the model.

## Stage A4 - multilingual and voice

- Chat replies: written directly in the question language where the model can, verified by the answer-language
  tier; a script that cannot be verified is reported as unverifiable rather than claimed.
- Evidence narratives: the same gate, with values withheld from translation and substituted back.
- dialogue.SCRIPTS grows with every language made writable, so the adherence check measures instead of passing
  silently.
- Voice (PS feature 8) keeps its recorded state: the Sarvam key is configured locally, and the recognition path
  is exercised only where it can be measured. Recognition confidence is never answer confidence.

## Stage A5 - hardening and transparency

- Provider policy recorded and readable: which policy is in force, which provider answered, latency, tokens, the
  failover chain, and what happened when a provider failed.
- One HTTP surface naming the live planner, the provider order and the last failure, so a reader never has to
  guess why an answer is slow.
- Planning and composition calls are bounded (tokens, timeout) and their latency is measured per turn; the chat
  stage line already reports the engine own checkpoints.

## Front end: keep the zero-build workspace, do not move to React in this batch

The desktop surface is 19 hand-built views over a strict CSP (script-src self only), an audit that reads the
served files, and ten component suites. Nothing the chat overhaul needs is blocked by it: staged progress, quick
replies, a reading line and a register switch are all already served. A React migration would rewrite every view,
add a build step to a workspace whose audit deliberately reads served source, and put the component suites and
their evidence behind a bundler - a large regression risk for no capability the product is missing.
**Recommendation: not now.** If it is wanted later it is its own batch with its own acceptance run, and the
honest intermediate step would be one framework-authored island (for example the transcript) behind the same CSP
rather than a rewrite.

## Acceptance evidence

- measured journeys with the live provider chain: greeting, thank-you, capability question, simple logic,
  out-of-scope question, a weather question with retrieval, a follow-up, and a non-English greeting, recorded
  with provider, model, latency, planner policy, status and the leakage check;
- component checks for the conversational status, the new intent schema and the planner policy;
- the standing gates: scripts/verify_all.py, the frontend audit, the status-drift check.

## Delivered: the model plans, and a conversation is a real answer

**Stage A1 — the planner is the model.** ModelRouter plans with the provider chain by default; the
deterministic rules plan only when the policy says so, and the policy is recorded in
trace.planning.planner_policy on every turn. A provider outage names every provider tried and is never
quietly answered from the rules floor. A plan the model cannot make valid is repaired with the validator own
message, and if it still fails the turn degrades to a readable answer with the reason in the trace instead of
raising at the reader - which is what used to happen to "hello".

**Stage A2 — conversational turns.** A greeting, a thank-you, a capability question, general reasoning, a
meta question or an out-of-scope message is planned as one chat task with the reply written beside it from a
deterministic workspace picture (the clock, the callable tools, the source ledger counts and what this
workspace does not do). No tool runs and nothing is acquired. The reply is checked before a reader sees it:

- a measurement unit (including spelled-out forms),
- a date or a time,
- a number standing beside a weather word,
- a warning claim (a colour plus alert, a warning header, or a warning word with a claim verb),
- a source identifier or a link,
- a present-weather claim about a place,

each reject the reply, and one repair attempt is made with the violation named in the prompt. A reply that still
fails is withheld, and the turn says so. General reasoning that needs no source - arithmetic, a definition - is
allowed and is told to present itself as general knowledge. The turn carries status conversation, empty facts
and citations, the note that no source was read, and a visible "No source read" tag on the card. A
conversational reply never becomes retrievable evidence: the conversation state keeps the exchange and drops
any last_evidence.

**Measured live (16 September 2026)** with the workspace own provider order (OpenRouter free first, local
Ollama second; both available), recorded in research/reviews/chat-overhaul-20260916/journeys.json:

| Message | Planner | Seconds | Result |
| --- | --- | --- | --- |
| "hello" | openrouter, policy model | 11.0 | conversation; a natural greeting, no acquisition |
| "what can you do?" | openrouter | 19.3 | conversation; names the real tools and what it cannot do, from the ledger |
| "what is 17 times 3?" | openrouter | 48.3 | conversation; "fifty-one", stated as general knowledge, not a measurement |
| "नमस्ते" | openrouter | 9.3 | conversation in Devanagari; language_adherence written_in_requested_script |
| "Will it rain in Surat tomorrow morning?" | openrouter | 19.5 | answered; 1 fact, 0.4 mm, GFS, three quick replies |
| "thanks!" (same conversation) | openrouter | 19.5 | conversation; continuity kept |

No turn needed a repair, and the leak check passed on every conversational reply. A real browser run on the
same build (Chrome 153 over CDP, 1280x900, recorded in research/reviews/chat-overhaul-20260916/browser-conversation.json)
asked "hello" and got the card titled **Conversation**, tagged *Conversational reply · No source read · 16 Sept
2026, 22:44 IST*, with the answer "Hello! How can I help you with weather information today?", zero fact rows,
zero receipts and no headline number. The weather turn kept the
evidence path exactly as it was: the fact is tool-owned, the source is named, and the renderer is
typed_task_renderers.

**What the leak check is and is not.** It is a bounded heuristic over one reply, not a proof: a number written
as a word ("fifty-one") passes it, and a claim phrased outside the patterns could pass too. The structural
guarantees are what a reader can rely on: a conversational turn acquires nothing, holds no fact, cites nothing,
is labelled a conversational reply on the card, and is never stored as evidence. The patterns reduce the risk of
a weather claim in prose; they do not replace that structure.

**Latency is the open cost.** Planning is 9-47 s on the free provider, and a chat turn is one planning call
with a repair call only when a reply is refused. The reading line and the engine own stage line cover the wait
for questions the deterministic rules can read, but a greeting has no reading to show. A cheaper routing tier
(a short classification call before the full plan) is the candidate fix, not built here.

## Delivered after the first measurement: the cheap first look, the frozen provider, the written answer

### The cheap first look (stage A2.5)

A short routing call now runs before the planner: it decides *conversation or task* against a ~700-character
workspace picture, and a conversation is answered in that same call. A task falls through to the full planner,
which still owns every plan, so nothing is planned more cheaply than before. The route the model cannot decide
is a task, and a first look that fails or exceeds its 12 s budget changes nothing. The tier decides no value:
the reply it returns is checked by the engine exactly as a planned reply is.

Measured on the same afternoon and the same provider order (research/reviews/chat-overhaul-20260916/router-tier-and-quota.json):

| Message | Before | With the first look |
| --- | --- | --- |
| "hello" | 11.0 s | **4.2 s** |
| "what can you do?" | 19.3 s | **4.2 s** |
| "what is 17 times 3?" | 48.3 s | **8.0 s** (and it now answers "51" as general knowledge) |
| "नमस्ते" | 9.3 s | 10.1 s |
| weather question | 19.5 s | 102.4 s in that run - see below |

The cost is real and measured: a task turn pays for the first look as well, about 3-4 s more than before, and
the switch can be turned off per workspace (WEATHERGPT_ROUTER=off). The 102 s weather turn was the written
answer's tail latency, not retrieval: a **25 s wall-clock budget for the whole composition step** was added in
response (measured after that run: a refused or slow composition now falls to the tool-owned facts within the
budget, and the planner step itself is bounded at 45 s, so a refused provider reaches the reader in about a
minute instead of a two-minute retry loop).

### The provider policy is frozen to the free cloud models (reader decision, 16 September)

WEATHERGPT_PROVIDERS=cloud_free is the default: only the curated free OpenRouter ids answer, ordered most
capable first and failing over between them. The local model runs only under WEATHERGPT_PROVIDERS=local, which
is kept for diagnosing an offline machine and is not a fallback that runs by itself. With no key configured
there is no provider at all, and the planner says so rather than routing around it. The policy is recorded in
every planning and composition trace (`provider_policy`), and `ModelRouter.state()` reports the policy, the
planner policy, the first-look switch and each provider's availability.

### The written answer for a turn with facts (stage A3)

A turn that retrieved facts now asks the model for the reader's answer in two or three sentences, from those
facts only, behind the checks that already covered model text: every number must come from the facts, every
measurement must match a fact's own unit (the unit set is read from the facts, so a changed unit is caught as a
changed unit), the place the facts belong to must be named, the supporting evidence ids must exist, and no
link, certainty or unrequested language may appear. Any failure - including a slow or refused call, bounded at
25 s for the whole step - leaves the tool-owned renderer stating the facts, with the refusal recorded in
`trace.generation`. The fact rows, ruler and receipt stay tool-owned on the card; the claim-attribution
invariant now reads "the model may write the answer, and it may not rewrite what the facts say", which
tests/test_product_stage_one.py exercises with a changed value, a changed unit and a lost place.

### DeepSeek integration (16 September 2026, at the reader request)

The OpenRouter free-models-per-day quota was exhausted, so the reader supplied a DeepSeek key. It is stored in
`data/runtime/model-config.json` (git-ignored, never logged, never returned) and the reader set the policy to
`deepseek_first`. It is a **paid** endpoint billed to that key, and prompts leave the machine: that trade is
the reader's stated choice, not a silent one.

- `DeepSeekClient` speaks the OpenAI-compatible endpoint at api.deepseek.com with `deepseek-chat`. DeepSeek
  accepts a JSON object reply, not a JSON schema on the wire, so the schema travels in the system message and
  the reply is parsed with the same tolerance the OpenRouter client uses (extract_json), then validated exactly
  as before. The trace records the model, the attempt count, the latency and the tokens (including cache hits),
  so a paid turn can be accounted for.
- `WEATHERGPT_PROVIDERS` now takes `deepseek_first` (the reader's choice), `deepseek`, `cloud_free` or `local`.
  The default is `deepseek_first` when a DeepSeek key is configured and `cloud_free` otherwise. The free
  OpenRouter ids stay behind the paid endpoint as failover, so a key problem does not stop the workspace, and
  the deepseek-only policy with no key has no provider at all rather than falling back on its own.
- A refused key (401/403) disables the client for the process; a missing balance (402) is named as such; a rate
  limit or a server error is retried once and then the router moves on.

### Measured on DeepSeek: six live journeys, no failures

`research/reviews/chat-overhaul-20260916/journeys-deepseek.json`, same runner as before:

| Message | Free provider | DeepSeek | Result |
| --- | --- | --- | --- |
| "hello" | 11.0 s | **0.93 s** | conversation, natural greeting |
| "what can you do?" | 19.3 s | **1.11 s** | conversation, names the tools and the limits |
| "what is 17 times 3?" | 48.3 s | **0.89 s** | conversation, "51", stated as general knowledge |
| "नमस्ते" | 9.3 s | **1.14 s** | conversation in Devanagari |
| "Will it rain in Surat tomorrow morning?" | 19.5 s | **5.94 s** | answered; written answer, 1 fact, 0.4 mm, GFS |
| "thanks!" | 19.5 s | **0.73 s** | conversation, continuity kept |

### What the written answer does now, and where it stops

The written answer applies to a **point reading** - a forecast, an observation, a wave or discharge figure -
where the deterministic text is a short sentence list (at most four lines, 600 characters). A published
historical table, a quoted bulletin passage, an advisory extract or a long hourly series keeps its own
renderer: the model does not rewrite a record that was laid out to be read. Measured on the marine turn
("What is the sea like near Kochi tomorrow?", 72 hourly facts): the typed renderer still draws the rows, and no
model text replaces them.

The place label, the window label and the source clause are **tool-owned strings**: the narrative prompt
receives `place_label` ("Surat", not the gazetteer's "Surat, Sūrat, State of Gujarāt"), a pre-rendered
`window_label` ("17 Sep 2026 09:30-12:30 IST"), and the answer carries the source clause from the deterministic
text ("Source: GFS forecast; conditions can change."). A measured turn reads: *"In Surat, for the window 17 Sep
2026 09:30-12:30 IST, the forecast rainfall is 0.4 mm. This is a model forecast at the selected place point, not
an observation or district average. Source: GFS forecast; conditions can change."*

### Measured incident: the free quota ran out

Later the same afternoon, every cloud-free call was refused: `HTTP 429 Rate limit exceeded: free-models-per-day.`
With the cloud-only policy frozen and nothing else enabled, a turn reports "No model provider could answer"
honestly and holds its facts - measured on "thanks!" at 53.8 s before the step budgets were added, and on
"hello" at 52.5 s after them (12 s first look + 45 s plan, both refused). Options are recorded, not chosen
here: wait for the daily reset, add a small credit to the account, lower the request count with
WEATHERGPT_ROUTER=off, or unfreeze the local model - which the reader deliberately froze.

### Stage A4: language breadth, measured (16 September 2026)

**The adherence table is the registry now.** `dialogue.SCRIPTS` held two entries (Hindi, Gujarati), so an
answer promised in Tamil, Bengali, Punjabi, Odia, Kannada, Telugu, Malayalam, Marathi or Urdu was never
checked at all. It is derived from the language registry, so all 22 measurable languages are checked, and a
language added there is measured rather than passing silently. English and romanised Hinglish share the Latin
script and cannot be checked this way; they say so instead.

**A romanised request is no longer reported as "not applicable".** Measured need: a reader asking for
`hi-Latn` got an English answer and a trace that said nothing had been asked for. The tier now reports
`unverifiable_script` and tells the reader the answer stays in its source language, because the request was
made and not met.

**Measured delivery, ten languages, one weather question each with an explicit output language**
(`research/reviews/chat-overhaul-20260916/languages.json`):

| Requested | Status | Adherence | Result |
| --- | --- | --- | --- |
| hi, gu, ta, mr, pa, od, ur | answered | rendered_with_protected_values | rendered, every value as the original characters (6.5-9.1 s) |
| bn, ml | **partial** | values_did_not_survive | the service dropped protected placeholders on the written sentence, so the source-language answer was kept and the refusal recorded |
| hi-Latn | answered | unverifiable_script | not claimed: the answer stays in its source language and says so |

The two failures are the translation service losing placeholders, not a gap in the protection patterns: the
sentence that failed carried a protected named date, two protected clocks, a protected unit value and a
protected place, and the gate refused the rendering rather than showing a partly rewritten value. That is the
contract working, and it is the honest outcome: seven languages rendered, one was never claimed, two were
refused and said so.

### C2: the continuity journeys, measured with a reachable planner (16 September 2026)

With the model planner reachable again, the four journeys the earlier chat batch could not measure were run
against the real engine (`research/reviews/chat-overhaul-20260916/continuity.py`, record in `continuity.json`):

| Journey | Result |
| --- | --- |
| forecast, then "and tomorrow afternoon?" | answered; `follow_up`, only `time` changed, place **Surat retained**, window moved to 12:30-18:30, same source S21 |
| then "what about the evening?" | answered; `follow_up`, place retained, window 18:30-22:30 |
| "no, I meant Ahmedabad" | answered; `correction`, only `places` changed, the 09:30-12:30 window **kept** |
| "thanks! and tomorrow?" | answered; `follow_up`, place retained, window moved - a greeting attached to a request does not swallow the request |
| an ambiguous name, then "the one in Gujarat" | the ambiguous name is disclosed ("Springfield is ambiguous; no state or district was supplied, so the name is used as given") with the resolved label on the card; the refinement is refused honestly ("I could not find a settlement named Springfield in Gujarat... I will not replace it with a nearby city") |

The measurable half of this is pinned in `tests/test_continuity_journeys.py`: a continuation that names no place
keeps the accepted place and the source and moves the window; a correction replaces the place and keeps the
window; a greeting attached to a request still retrieves. What the suite cannot pin is the model own reading, so
the live record is kept beside it.

## Still to come in this batch

- **Stage A3**: a model-written narrative sentence for evidence answers behind the existing validation, with the
  tool-owned fact renderer as the floor. Today a turn with facts is still rendered by the deterministic
  renderer, which is honest but terse.
- **Stage A4 (delivered, 16 September)**: dialogue.SCRIPTS is derived from the language registry (22
  measurable languages instead of two), a romanised request is reported as unverifiable rather than "not
  applicable", and delivery was measured live for ten languages - seven rendered with protected values, two
  refused because the service dropped placeholders, one never claimed.
- **Stage A5 (delivered, 16 September)**: the settings surface now states who answers, in what order, the
  planner policy, whether the cheap first look is on, the availability of each provider, and the last time
  every provider refused with its reason and time. The payload comes from `ModelRouter.state()`; the router
  records a failure per refused client and, if none answers, the whole chain. `scripts/models.py --set-key`
  takes `openrouter` (default) or `deepseek`, so the command printed in the UI is a command that works.

## What this batch does not establish


It does not claim the model always decides well, does not turn model prose into evidence, does not publish
runtime conversations, and does not claim language coverage beyond what a gate has measured. Voice and mobile
remain incomplete requirements, not cancelled ones.
