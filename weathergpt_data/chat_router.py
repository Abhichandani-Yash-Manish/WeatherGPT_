"""A cheap first look at a message: is this a conversation, or a task for the governed tools?

Measured 16 September 2026: a conversational turn paid for the whole planner prompt - the task catalogue,
the workspace picture and the dialogue schema - and took 9-48 s on the free provider, almost all of it the
model reading a long prompt to say "hello". This tier asks a short question first: conversation, or task.
A conversation is answered in the same call. A task falls through to the full planner, which still owns
every plan, so nothing is planned more cheaply than before.

It decides no value. The reply it returns is checked by the engine exactly as a planned reply is, and a
route the model cannot decide is a task, so the safe path is the default. A call that fails, returns
something unrecognised, or comes back as a task leaves the turn to the full planner.
"""
import json
import os

from .language import expand_request, obj, string, validate_plan
from .transport import SourceError

# A first look that cannot answer quickly is not worth waiting for: the planner can still take the
# turn. Measured tail latency on a free endpoint is tens of seconds, while a normal first look is a
# few seconds, so a bounded call keeps the router from becoming the slow path it exists to remove.
ROUTER_TIMEOUT = float(os.getenv('WEATHERGPT_ROUTER_TIMEOUT') or 12.0)

ROUTER_KINDS = ['greeting', 'thanks', 'capability', 'meta', 'logic', 'small_talk', 'out_of_scope', 'task']
ROUTER_SYSTEM = (
    "You are the first reader of one message for WeatherGPT, a local weather workspace. Never describe" 
    " yourself as a front desk, a router or a tier: write any reply in the first person as the assistant."
    " Read one message and decide what it"
    " needs. Answer with kind=task when it asks for weather, a warning, a document, a historical value or any"
    " other evidence this workspace holds: a task is then planned in full by another tier, so never answer it"
    " here. Answer with one of greeting, thanks, capability, meta, logic, small_talk or out_of_scope when it"
    " needs no evidence, and write the reply in the reply field. A reply must contain no weather value,"
    " forecast, warning, date, time or place-specific fact, and no measurement of any kind; for capability or"
    " meta questions, describe only the tools and limits in the workspace picture. General reasoning that needs"
    " no source - arithmetic, a definition - may be answered from general knowledge, and the reply must say that"
    " it is general knowledge. Be brief, natural and useful, under 70 words, in the language of the message."
    " When the message greets and also asks for weather, the kind is task. Return JSON.")


def router_enabled():
    """Whether the cheap first look runs. It is on by default and can be switched off per workspace."""
    import os
    from .providers import local_config
    value = str(os.getenv('WEATHERGPT_ROUTER') or local_config().get('chat_router') or 'on').strip().lower()
    return value not in {'off', 'false', '0', 'no'}


def chat_plan(question, kind, reply, language='en'):
    """The plan for a conversational message, built and validated like any other plan."""
    if not isinstance(reply, str) or not reply.strip():
        raise SourceError('A conversational plan needs the reply the model wrote')
    request = {'language': language, 'places': [], 'assumptions': [], 'clarification': '',
               'explicit_times': False,
               'tasks': [{'request_quote': question[:80], 'kind': 'chat', 'operation': 'reply',
                          'parameters': [], 'years': [], 'period': 'annual', 'start_local': '',
                          'end_local': '', 'place_indices': [], 'reply': reply}],
               'context_action': 'new', 'changed_fields': []}
    plan = expand_request(request)
    validate_plan(plan)
    return plan


def route(model, question, now, history, brief=None):
    """(plan, meta) when the message is a conversation, or None to let the full planner run."""
    from .workspace_brief import brief as workspace_brief
    recent = [message for message in (history or []) if isinstance(message, dict) and message.get('content')][-3:]
    payload = {'message': question, 'recent_conversation': recent,
               'workspace': brief if brief is not None else workspace_brief(now, limit=700, tool_names_only=True)}
    data, meta = model.complete(ROUTER_SYSTEM, json.dumps(payload, ensure_ascii=False),
                                obj({'kind': {'type': 'string', 'enum': ROUTER_KINDS}, 'reply': string()}),
                                max_tokens=320, timeout=ROUTER_TIMEOUT)
    if not isinstance(data, dict):
        return None
    kind = data.get('kind')
    reply = data.get('reply')
    if kind not in ROUTER_KINDS or kind == 'task':
        return None
    if not isinstance(reply, str) or not reply.strip():
        return None
    try:
        plan = chat_plan(question, kind, reply.strip())
    except (SourceError, TypeError, KeyError, ValueError):
        return None
    meta = dict(meta or {})
    meta.update(planner_tier='router', chat_kind=kind)
    return plan, meta
