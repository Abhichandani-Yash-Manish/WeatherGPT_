# Intelligent chat overhaul: the model owns the conversation, the tools own the facts

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

## Still to come in this batch

- **Stage A3**: a model-written narrative sentence for evidence answers behind the existing validation, with the
  tool-owned fact renderer as the floor. Today a turn with facts is still rendered by the deterministic
  renderer, which is honest but terse.
- **Stage A4**: evidence narratives through the language gate for more languages, and dialogue.SCRIPTS widening
  with each language made writable.
- **Stage A5**: the provider and planner policy surfaced in the settings and health surfaces, so a reader can
  see which provider is answering and what last failed.

## What this batch does not establish


It does not claim the model always decides well, does not turn model prose into evidence, does not publish
runtime conversations, and does not claim language coverage beyond what a gate has measured. Voice and mobile
remain incomplete requirements, not cancelled ones.
