"""The deterministic picture of this workspace, for composing a conversational reply.

A conversational turn retrieves nothing, so the model has no evidence to write from. What it does have
is this workspace: the tools it can actually call, the sources the ledger says are connected, and what
that ledger says is blocked. Those come from the registries, never from the model's memory of itself,
which is how "what can you do?" came to be answered vaguely before this module existed.
"""
import json


def wired_source_ids():
    """The ids the ledger says an ordinary conversation can reach.

    A conversational reply has no evidence, and the one thing it must not do is explain that absence
    with a claim about this workspace that is false. Measured 21 September 2026: "why?" after a warning
    turn was answered "no source is wired to this chat, so I have no evidence to draw on" - from a
    workspace with sources wired. The claim is checkable, so it is checked.
    """
    return sorted(row['id'] for row in _ledger_rows() if row.get('connector', {}).get('wired_to_chat'))


def _ledger_rows():
    """The source ledger's rows, or none.

    `wired_to_chat` is nested under `connector`, and it is a different fact from `connected`: the
    first says an ordinary conversation can reach the source, the second that a registered connector
    ingests it. This module read the flag at the top level, where it does not exist, so the workspace
    picture handed to a conversational turn said no source was wired to chat - and a reply explained
    its own lack of evidence with exactly that (measured 21 September 2026: "why?" after a warning turn
    came back "no source is wired to this chat, so I have no evidence to draw on"). The model was not
    inventing; it was repeating a false input, which is worse.
    """
    from .foundation import ROOT
    try:
        ledger = json.loads((ROOT / 'data/registry/source-review.json').read_text())
    except (OSError, ValueError, TypeError):
        return []
    return [row for row in (ledger.get('sources') or []) if isinstance(row, dict)]


def brief(now, limit=1500, tool_names_only=False):
    """The workspace as data: clock, callable tools, source ledger counts, and what it does not do.

    Bounded on purpose: a conversational reply needs a picture, not an inventory dump, and the
    planner prompt is already long. Tools are dropped from the end when the picture will not fit.
    tool_names_only serves the cheap routing tier, which needs to know what exists, not what each
    tool does.
    """
    from zoneinfo import ZoneInfo
    from .capabilities import planner_catalogue
    from .foundation import ROOT
    tools = [({'tool': c.get('tool')} if tool_names_only
              else {'tool': c.get('tool'), 'kind': c.get('kind'), 'purpose': c.get('purpose')})
             for c in planner_catalogue()]
    rows = _ledger_rows()
    sources = {'registered': len(rows) or None, 'status_counts': {}, 'blocked_access': []}
    if rows:
        sources = {'registered': len(rows),
                   'connected': sorted(row['id'] for row in rows
                                       if row.get('connector', {}).get('connected')),
                   'wired_to_chat': sorted(row['id'] for row in rows
                                           if row.get('connector', {}).get('wired_to_chat')),
                   'blocked_access': sorted(row['id'] for row in rows if row.get('status') == 'blocked_access')}
    payload = {'now_ist': now.astimezone(ZoneInfo('Asia/Kolkata')).isoformat(timespec='minutes'),
               'callable_tools': tools,
               'sources': sources,
               'not_available': ['official warning dissemination or alerts sent anywhere',
                                 'forecast skill, confidence or risk scores',
                                 'personalised advice beyond the published source']}
    text = json.dumps(payload, ensure_ascii=False)
    while len(text) > limit and payload['callable_tools']:
        payload['callable_tools'] = payload['callable_tools'][:-1]
        text = json.dumps(payload, ensure_ascii=False)
    return text if len(text) <= limit else json.dumps({k: v for k, v in payload.items() if k != 'callable_tools'},
                                                      ensure_ascii=False)[:limit]
