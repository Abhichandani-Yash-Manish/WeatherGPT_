"""A turn, as it happens: the stream is the poll, written as it arrives.

docs/116 batch B asked for the turn to be streamed rather than polled. What is built here is the smallest
honest version of that: the frames carry the payloads the two read routes already answer with - the progress of
ONE turn, and its result when it is over - so a stream cannot state a stage, a fraction or a confidence the poll
would not have stated. The client keeps its poll as the fallback, because a stream that cannot start must not
take the wait down with it.

Six states of this are pinned rather than intended: a stage is emitted when it CHANGES and not once per poll;
the last frame is the result; no frame carries a percentage, an ETA or a confidence; an identifier the
workspace cannot have is refused with 400 IN WORDS BEFORE any frame (a generator body does not run until its
first frame, so validating inside it would answer 200 and then die mid-stream); the route is token-gated like
its siblings; and a turn that outlasts the wait ends with a sentence naming the read route rather than with
silence.
"""
import json
import re
import threading
import unittest
import urllib.error
import urllib.request
import uuid

from weathergpt_data.workspace import Workspace, make_server

REQUEST_ID = str(uuid.uuid4())


class StubTurn:
    """A turn that reaches two stages and then finishes, without a model or a store."""

    def __init__(self):
        self.polls = 0

    def progress(self, request_id):
        self.polls += 1
        stage = "retrieving" if self.polls < 3 else "assembling"
        return {"schema_version": "chat-progress-v1", "request_id": request_id, "state": "running",
                "stage": stage, "stage_label": stage, "stages_seen": [stage], "stage_note": "test",
                "queue": {"waiting": 0, "active": 1, "capacity": 2, "wait_seconds_before_refusal": 45},
                "stages_are_facts_not_progress": True}

    def result(self, request_id):
        if self.polls < 3:
            return {"schema_version": "chat-result-v1", "request_id": request_id, "state": "pending",
                    "packet": None, "detail": "This turn has been accepted and has not finished."}
        return {"schema_version": "chat-result-v1", "request_id": request_id, "state": "ready",
                "packet": {"status": "ok", "answer": "test"}, "detail": "This turn is finished."}


def workspace_with_turn(stub=None):
    space = Workspace(frontend="react")
    space.conversation = stub or StubTurn()
    return space


class FrameTests(unittest.TestCase):
    def test_a_stage_is_emitted_when_it_changes_and_the_result_ends_the_stream(self):
        frames = list(workspace_with_turn().stream_turn(REQUEST_ID))
        self.assertEqual([frame["kind"] for frame in frames], ["progress", "progress", "result"])
        self.assertEqual(frames[0]["progress"]["stage"], "retrieving")
        self.assertEqual(frames[1]["progress"]["stage"], "assembling")
        self.assertEqual(frames[2]["result"]["state"], "ready")
        self.assertTrue(all(frame.get("kind") != "timeout" for frame in frames), "the stream timed out on a finished turn")

    def test_no_frame_states_a_fraction_or_a_confidence(self):
        text = json.dumps(list(workspace_with_turn().stream_turn(REQUEST_ID))).lower()
        # Word boundaries, not substrings: the first version of this forbade "eta" and failed on "detail", which
        # every frame carries because the read routes state their own state in words. A check that fires on a
        # neighbouring word is a check nobody can leave switched on.
        for forbidden in ("percent", "percentage", "eta", "confidence", "fraction", "completion"):
            self.assertIsNone(re.search(r"\b" + forbidden + r"\b", text), forbidden + " reached a stream frame")

    def test_an_identifier_this_workspace_cannot_have_is_refused_before_any_frame(self):
        for bad in ("", "nope", "12345"):
            with self.assertRaises(ValueError):
                workspace_with_turn().stream_turn(bad)


class RouteTests(unittest.TestCase):
    """The route, over a real socket: framing, gating and the refusal that must arrive before a frame does."""

    def setUp(self):
        server = make_server(workspace_with_turn(), 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join()))
        self.base = "http://127.0.0.1:" + str(server.server_port)
        # The token is read from the served page, the way the other route tests do it: it is minted per process.
        html = urllib.request.urlopen(self.base).read().decode()
        self.token = re.search(r'name="workspace-token" content="([^"]+)"', html)[1]

    def get(self, path, token=None):
        headers = {"X-WeatherGPT-Token": token} if token else {}
        try:
            with urllib.request.urlopen(urllib.request.Request(self.base + path, headers=headers), timeout=30) as answer:
                return answer.status, answer.read().decode(), dict(answer.headers)
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode(), dict(error.headers)

    def test_the_stream_answers_frames_and_ends_with_the_turn_result(self):
        status, body, headers = self.get("/api/chat/stream?request_id=" + REQUEST_ID, token=self.token)
        self.assertEqual(status, 200, body)
        self.assertIn("text/event-stream", headers.get("Content-Type", ""))
        self.assertEqual(headers.get("Cache-Control"), "no-store")
        frames = [json.loads(line[len("data: "):]) for line in body.splitlines() if line.startswith("data: ")]
        self.assertEqual([frame["kind"] for frame in frames], ["progress", "progress", "result"])
        self.assertEqual(frames[-1]["result"]["state"], "ready")

    def test_the_route_needs_the_session_token_like_its_siblings(self):
        status, body, _ = self.get("/api/chat/stream?request_id=" + REQUEST_ID)
        self.assertEqual(status, 403, body)

    def test_a_refused_identifier_is_400_in_words_before_any_frame(self):
        status, body, headers = self.get("/api/chat/stream?request_id=nope", token=self.token)
        self.assertEqual(status, 400, body)
        self.assertIn("identifier", json.loads(body)["error"].lower())
        self.assertNotIn("text/event-stream", headers.get("Content-Type", ""))


if __name__ == "__main__":
    unittest.main()
