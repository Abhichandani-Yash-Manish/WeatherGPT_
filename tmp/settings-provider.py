import pathlib
p = pathlib.Path('weathergpt_data/product_api.py')
t = p.read_text()
anchor = "    return envelope('settings.capabilities', 'ok',"
assert t.count(anchor) == 1, t.count(anchor)
t = t.replace(anchor, "    from .providers import RULE_MODEL, free_model_choices, key_source\n    choices = free_model_choices()\n    configured = key_source() != 'not configured'\n    provider = {'rules_floor': {'model': RULE_MODEL, 'available': True,\n                                'detail': 'the core question shapes are planned with no model at all'},\n                 'openrouter': {'configured': configured, 'key_source': key_source(),\n                                'routing_order': list(choices.get('routing_order') or []),\n                                'refused': list(choices.get('refused') or []),\n                                'note': ('Only ids ending in :free are routed. The order is a capability judgement for this workload, '\n                                         'most capable first, not a provider statement, and only a keyed probe measures what the '\n                                         'account can actually reach.')},\n                 'set_key_command': 'python3 scripts/models.py --set-key',\n                 'probe_command': 'python3 scripts/models.py --probe-free',\n                 'key_note': ('The key is written to local configuration on this machine with owner-only permissions, is never sent '\n                              'anywhere except the provider it belongs to, and is never printed by the workspace.')}" + chr(10) + anchor, 1)
old_data = "                     'connected_sources': len([s for s in sources if s['integration_status'] == 'prototype_adapter_tested'])},"
assert t.count(old_data) == 1, t.count(old_data)
new_data = "                     'connected_sources': len([s for s in sources if s['integration_status'] == 'prototype_adapter_tested']),\n                     'provider': provider},"
t = t.replace(old_data, new_data, 1)
old_limits = "                    limitations=['A registered source is not a serving approval, and a connected adapter is not operational readiness.',"
assert t.count(old_limits) == 1
t = t.replace(old_limits, old_limits + chr(10) + "                                 'The model routing order is a capability judgement for this workload, not a provider statement; only the keyed probe measures availability.',", 1)
p.write_text(t)
print('patched settings view')