# 116 — The chat, reviewed and planned

20 September 2026. The chat is the core of this product and it does not yet work perfectly. This is what
is actually wrong with it, found by exercising it rather than by reading it, and what to do about it.

Everything below was measured against the running engine on this machine.

## 1. What is already right

Worth stating first, because it narrows the problem and because these are the hard parts:

| Asked | Answered |
| --- | --- |
| "Who is the prime minister of India?" | Refuses: holds no such information, names its own scope. No invention. |
| "What is the weather in Zzyzxville?" | "I could not find a settlement named Zzyzxville… I will not replace it." |
| "अहमदाबाद में कल बारिश होगी?" | Answers in Hindi, with a real fact and its window. |
| 1400 characters of noise | "Enter a question of 1–1500 characters." |

Latency is not the problem either. A greeting answers in ~1.1 s, a forecast in ~3–6 s, and a cold first
model call in ~30 s. The 40-second turns seen earlier were cold starts, not the steady state.

## 2. Four defects found, and fixed

**An abandoned turn owned the conversation that replaced it.** The reducer guarded `preview`, `progress`,
`stopping` and `stopped` by the turn's key and never guarded `answer` or `notice`. A request still in
flight when the reader started a new conversation landed in that new conversation, and a refusal
additionally put its question back into a composer the reader had moved on from.

**The abort did nothing.** `send` created an `AbortController`, stored it in a ref, and never passed it to
anything. `chat.ask` had accepted a signal all along. A turn the reader walked away from ran to completion
against a server that had been asked for nothing.

**Kochi in Kerala was the fifth Kochi.** Five places share the name and all five are `PPL`, so seat order
ties and the catalogue id decides. The id was compared as a *string*, so `geonames:10453626` sorted before
`geonames:1273874` and four Maharashtra villages were offered ahead of the port. A number sorts as a
number now; this is a corrected comparison and not a prominence ranking, which the gazetteer has no data
for.

**"and tomorrow?" answered with yesterday.** The worst of the four. The context resolution was right — it
carried the place and measures, marked the time changed, and resolved tomorrow's window — and then the
inheritance block copied the prior task's `kind` over it. The prior kind was `observation`, and an
observation read for a future window answers with the latest *past* reading. The second turn returned the
first turn's six facts verbatim, as the answer to a question about tomorrow, with nothing saying they were
not. The operation is no longer inherited when the window has moved past what the prior one covered.

## 3. What is still architecturally wrong

### 3.1 There is no streaming

`/api/chat` is one POST that resolves with the whole packet. Nothing is readable until everything is
ready. At 3–6 s this is tolerable and at 30 s it is not, and the reader has no way to tell which they are
in for.

The server is a `ThreadingHTTPServer`, so a long-lived response holds a thread and Server-Sent Events are
available without changing the server model. The sentence is generated last, after retrieval, so the
honest thing to stream is not tokens but **stages and facts**: the place as soon as it resolves, each
claim as its source answers, the sentence last.

That ordering also happens to match the product's ethic — evidence first, prose over it.

### 3.2 Progress is global, not per turn

`/api/chat/progress` returns `self.conversation.progress()` — the workspace's single conversation. Two
tabs, or a turn started while another is running, read each other's stage. The endpoint takes no request
id and the client sends none.

Progress belongs to a request. It should be keyed by `request_id`, which the client already generates and
already sends to `/api/chat`.

### 3.3 The client polls

900 ms polling, so a 30-second turn costs about thirty-three extra requests to learn a stage name. Once
3.1 exists this disappears: the stage arrives on the same stream as everything else.

### 3.4 A turn cannot be resumed

A dropped connection loses the turn. The server has the answer and the client has the `request_id`, and
there is no route that trades one for the other. `GET /api/chat/result?request_id=…` would make a refresh
survivable.

## 4. What is still wrong for the reader

- **A question cannot be edited.** Every chat product lets a reader correct the question they just asked.
  Here the only path is to type it again.
- **An answer cannot be regenerated**, and for a product whose answers depend on a live read, "ask the
  sources again" is a more meaningful button than in most chat products. `Collect fresh evidence` exists
  on the card but is not offered as a re-ask.
- **Disambiguation costs a whole turn.** `needs_selection` returns a question and five chips; choosing one
  sends a new request. It could resolve inline without leaving the turn.
- **There is no way to change just the place or just the time.** A reader who wants the same question for
  a different place must rewrite the sentence and hope the planner agrees. The panel knows the place; the
  claim knows the window; neither is an affordance.
- **Nothing recovers a failed turn.** A refusal returns the question to the box, which is right, but there
  is no retry beside it.

## 5. The plan

| Batch | Work | Why this order |
| --- | --- | --- |
| A | Per-request progress: `request_id` on the progress route and the client | Small, and 3.2 is a correctness bug rather than a refinement |
| B | Stream the turn over SSE: stage → place → each claim → sentence | The largest single change to how the chat feels |
| C | Resume: `GET /api/chat/result?request_id=` | Falls out of B; makes a refresh survivable |
| D | Edit a question, retry a refusal, regenerate an answer | The three missing chat affordances |
| E | Inline disambiguation, and change-place / change-time on a turn | Turns two ideas the product already holds into controls |

A and C are small. B is the one that changes the product.

## 6. What this does not claim

The four defects in §2 are fixed and each is pinned by a spec. Nothing in §3 or §4 is built. The latency
figures are from one machine with a warm model and a local store, and the 30-second cold start will look
different on a machine that has not run this before. The truth behaviours in §1 were sampled, not proved:
four questions is not a guarantee about the refusal path.
