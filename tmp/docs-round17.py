import json, pathlib, datetime
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
root = pathlib.Path('.')
r = root / 'README.md'
t = r.read_text()
anchor = '- **Desktop web only.**'
assert t.count(anchor) == 1
bullet = '- **The conversation carries the artefacts.** Every answer offers what its own evidence supports: the right-now reading (stations with distance and age, the published day, the next model hours, and what is not connected), an alert brief or an advisory brief composed in place with save-to-briefcase, and a briefing written into the local series. Pending slots, retrieval coverage, the edition comparison and each edition printed issue date and currency render from the tools own records, and the trace names the provider, the model and any failover. The OpenRouter key goes in with one command: python3 scripts/models.py --set-key (hidden prompt, owner-only file, never printed), and only free model ids are ever routed, ranked most capable first, with the local model as the fallback. See [docs/61](docs/61-chat-surface-and-provider-ux.md).'
t = t.replace(anchor, bullet + chr(10) + anchor, 1)
doc_anchor = '- [State agromet coverage](docs/60-state-agromet-coverage.md)'
assert t.count(doc_anchor) == 1
t = t.replace(doc_anchor, "- [The chat surface and the key you paste](docs/61-chat-surface-and-provider-ux.md) - the audit that found a whole-turn renderer crash, the artefact actions now wired into the conversation, three place and freshness defects fixed, and the one-command OpenRouter key flow with a ranked free-model list." + chr(10) + doc_anchor, 1)
r.write_text(t)
h = root / 'data/registry/hardening-progress.json'
d = json.loads(h.read_text())
d['chat_surface_batch'] = {
    'report': 'docs/61-chat-surface-and-provider-ux.md',
    'evidence_directory': 'research/implementation/chat-surface-20260915',
    'operational_ready': False,
    'scope': "The chat surface, made to match the engine: an audit of fourteen live journeys, the renderer crash it found (table is not defined) repaired with an offline check, artefact actions in the conversation (right-now reading, alert brief, advisory brief, briefing), a retrieval account renderer for pending slots, coverage, edition comparison and editions read, provider transparency in the answer trace, tied-place resolution decided by the connected product with disclosure, station freshness leading the right-now reading, Indic day and part-of-day words with one definition per part of day, and the OpenRouter key flow: --set-key at mode 0600 with no echo, free-only routing enforced, twelve ranked free models, OpenRouter first with local failover (measured with an invalid key), and a settings card that shows the state and the commands.",
    'automated_tests': 846,
    'javascript_component_checks': 70,
    'measured': {'audit_journeys': 14, 'journeys_answered': 11, 'renderer_crash_found': 'table is not defined (a whole turn failed to render)',
                 'artefact_actions_verified_in_page': ['Right now here', 'Write the alert brief', 'Write the advisory brief', 'Write a briefing'],
                 'key_flow': {'command': 'python3 scripts/models.py --set-key', 'file_mode': '0600', 'key_printed': False,
                              'paid_ids': 'refused with a recorded reason', 'ranked_free_models': 12,
                              'provider_order': ['rules', 'openrouter (when configured)', 'ollama'],
                              'failover_measured': 'openrouter: the OpenRouter key was refused (HTTP 401), then the local model answered',
                              'valid_key_call': 'not made on this machine'}},
    'limitations': ['No valid OpenRouter call: the ranking stays a stated judgement until a key is probed.',
                    'One desktop viewport and one browser: no keyboard, screen-reader or mobile acceptance.',
                    'The place probes are a disclosed heuristic; a candidate with no product cell and no fresh station still asks.',
                    'No native-speaker review of the rendered languages.']}
d['updated_at_utc'] = now
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))
p = root / 'data/registry/product-progress.json'
pd = json.loads(p.read_text())
pd['as_of_utc'] = now
pd['latest_batch'] = 'docs/61-chat-surface-and-provider-ux.md'
p.write_text(json.dumps(pd, indent=2, ensure_ascii=False) + chr(10))
g = root / 'docs/31-full-solution-gap-register.md'
glines = g.read_text().splitlines()
inserted = False
for index in range(len(glines) - 1, -1, -1):
    if glines[index].startswith('- **R32 is recorded'):
        glines.insert(index + 1, "- **R33 is recorded in [docs/61](61-chat-surface-and-provider-ux.md).** The chat surface was audited against the live engine and then made to show it: a rendering crash (`table is not defined`, which stopped a whole turn from rendering) is repaired and pinned offline; every answer now offers the artefacts its evidence supports (right-now reading, alert brief, advisory brief, briefing) with save-to-briefcase where a brief exists; pending slots, retrieval coverage, edition comparison and each edition's printed issue date and currency are rendered from the tools' own records; the trace names the provider, model, model calls and failover. Three engine defects the audit exposed are fixed: a tied place name is decided by the connected product and disclosed (waves off Kochi answered instead of asking with four inland hamlets first), fresh stations lead the right-now reading (a five-month-old AWS row led it before), and English/Hindi/Gujarati now share one definition of 'morning' (the Indic word boundary bug meant 'સવારે' never matched at all). The OpenRouter key flow is one command (`scripts/models.py --set-key`, mode 0600, never echoed), paid ids are refused with a reason, twelve free models are ranked most-capable-first, and OpenRouter is tried before the local model with the refusal recorded as a failover - measured with an invalid key, as no valid key exists on this machine. **R33 closes no gap-register item**: no valid-key call, no mobile or screen-reader acceptance, and the place probes remain a disclosed heuristic. 846 Python tests and the 23-step verification passed at that checkpoint.")
        inserted = True
        break
g.write_text(chr(10).join(glines) + chr(10))
print('README', 'docs/61' in r.read_text(), '| batch', 'chat_surface_batch' in h.read_text(), '| R33', inserted)