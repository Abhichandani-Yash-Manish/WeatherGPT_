# 131 — The turn, as it happens: streaming the wait

20 September 2026. docs/116 batch B asked for the turn to be streamed rather than polled. This is what was
built, what it deliberately does not claim, and the measurement that says the mechanism is real.

## What a reader gets

The wait already said which stage the engine was in, up to 900 ms after it got there. It now says it when it
happens. Measured against a live turn on this machine, asking a real question of the running engine:

| Moment | What arrived |
| --- | --- |
| 404 ms | the stream opened and the first frame landed - the turn had started |
| 2825 ms | the engine's own `retrieving` stage |
| 6066 ms | `not_running` (progress), then the result frame with the packet |
| 6000 ms | the POST answered with the same packet |

So two thirds of a six-second wait was previously spent saying nothing, and is now spent saying what is
happening. The probe that produced those numbers is `research/reviews/frontend-batch-20260920/probe-stream.mjs`,
and it fails rather than passes if the frames arrive with the answer: a stream whose frames all land at the end
is the poll with one round trip more.

## What it is, exactly

`GET /api/chat/stream?request_id=` answers `text/event-stream` frames. **Every frame carries a payload one of the
two read routes already answers with** - the progress of that one turn, and its result when the turn is over - so
a stream cannot state a stage, a fraction or a confidence the poll would not have stated. It emits a frame when
the stage CHANGES rather than once per poll, and the payload's own honesty is untouched:
`stages_are_facts_not_progress` is still true, `stage_note` still says which state this is, and there is still no
percentage, no ETA and no confidence anywhere in it.

Two decisions are worth recording because both were defects when first written:

1. **The identifier is validated before the first frame.** A generator's body does not run until its first frame
   is asked for - which is after the status line has been sent - so validating inside the frame loop answers 200
   and then dies mid-stream. The validation happens in the function that RETURNS the generator, and a bad
   identifier is an ordinary `400` in words, which is what a reader can act on.
2. **The body is close-delimited, not chunked.** This server speaks HTTP/1.0 (`BaseHTTPRequestHandler` with no
   protocol override), so a response with no `Content-Length` ends when the connection does. That is what a
   stream is here, and it is the form that needs no change to how every other route on this server answers.

## The client

The wait follows the stream for its stages and **keeps its poll as the fallback**, which starts only after the
stream has FAILED: a workspace that cannot stream must still be able to say which stage it is in, and a healthy
stream must not double the reads. A test asserts exactly that - the spec runs a streamed turn for longer than the
poll's own interval and requires that `/api/chat/progress` was never called.

**The answer still arrives on the POST.** The stream does deliver the packet, and the client does not take it:
the POST already answers with it, and applying one answer twice is a different defect from the one this fixes.

One thing had to be moved rather than written: the frame reader was first written in `chat/api.ts`, and the
collection check refused it - *"every request goes through one place"*. It lives in `frontend/src/api/client.ts`
now, beside the token handling and the server's-own-words error mapping, which is where the product decided that
belongs. The check was right and the file was wrong.

## Evidence

| Check | Result |
| --- | --- |
| `python3 -m pytest tests/test_chat_stream.py -q` | **6 passed** - frames, order, the terminal state, no fraction or confidence in any frame, 400 before any frame, 403 without the token |
| `npx vitest run src/chat/stream.test.tsx` | **2 passed** - the stage comes from the stream and the poll is never opened; the poll takes over when the stream cannot be |
| the same spec, with the hook reverted to polling only | **1 failed** - so the check measures the stream rather than describing it |
| live probe against the running engine | **PROGRESSIVE**, first frame at 404 ms and the answer at 6000 ms |
| whole gate | **21 steps, 0 failed** - 1477 Python tests, 75 React suites, all four built-output audits |

## What batch B still does not do

- **Only the stage is streamed.** docs/116's sketch was *stage → place → each claim → sentence*; the place, the
  claims and the sentence still arrive together, in the POST's answer. Those are the parts that would make the
  answer itself appear progressively, and they are not built.
- **No cancellation or completion frame of its own.** A stopped turn is reported through the same progress and
  result payloads the polled routes use, not through a frame type of its own.
- **No reconnect.** A dropped stream falls back to the poll on the next send, not to a resume: there is no
  `Last-Event-ID` and no buffer, so a reader who loses the connection mid-turn waits for the answer as before.
- **Nothing was measured beyond one machine over loopback**, and the probe cannot see a phone, a slow network or a
  proxy that buffers - which is the classic way a stream stops being a stream in production.
- **No test covers a stopped turn's stream**, and none covers a turn that outlasts the two-minute wait (the code
  path exists and ends in a sentence, but nothing exercises it).

## A lesson the test taught

The first version of the spec enqueued both frames in one tick. React coalesced the two dispatches, the
intermediate stage was never painted, and the spec read as if the stream had not delivered it. The frames are
spaced in time now, because a burst is not a stream - and the same mistake, in a real browser, would look exactly
like a product that shows only the last stage.
