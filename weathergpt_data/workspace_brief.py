"""The deterministic picture of this workspace, for composing a conversational reply.

A conversational turn retrieves nothing, so the model has no evidence to write from. What it does have
is this workspace: the tools it can actually call, the sources the ledger says are connected, and what
that ledger says is blocked. Those come from the registries, never from the model's memory of itself,
which is how "what can you do?" came to be answered vaguely before this module existed.
"""
import json


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
    sources = {'registered': None, 'status_counts': {}, 'blocked_access': []}
    try:
        ledger = json.loads((ROOT / 'data/registry/source-review.json').read_text())
        rows = ledger.get('sources') or []
        sources = {'registered': len(rows),
                   'compiled_at_utc': ledger.get('compiled_at_utc'),
                   'status_counts': ledger.get('counts') or {},
                   'wired_to_chat': sorted(row.get('id') for row in rows if row.get('wired_to_chat')),
                   'blocked_access': sorted(row.get('id') for row in rows if row.get('status') == 'blocked_access')}
    except (OSError, ValueError, TypeError):
        pass
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
