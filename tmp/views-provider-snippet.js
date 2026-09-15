
    /* Which model answers, what it may spend, and where the key goes: the page states it rather
       than leaving the reader to read a config file. Nothing here prints or stores the key. */
    const provider = (view.data && view.data.provider) || null;
    if (provider) {
      const card = WG.block('Model providers',
        provider.openrouter.configured
          ? 'OpenRouter is configured; only free-tier model ids are routed, most capable first.'
          : 'No OpenRouter key is configured yet. The rules floor and any local model still answer.');
      card.append(WG.table(['Provider', 'State', 'Detail'], [
        ['Rules floor', 'always available', String((provider.rules_floor || {}).model || 'rule-planner') + ' — ' + String((provider.rules_floor || {}).detail || '')],
        ['OpenRouter', provider.openrouter.configured ? 'configured' : 'not configured',
          'key source: ' + String(provider.openrouter.key_source || 'not configured') + ' · ' + String((provider.openrouter.routing_order || []).length) + ' free model id(s) ranked'],
        ['Key handling', 'local only', String(provider.key_note || '')]
      ]));
      if ((provider.openrouter.routing_order || []).length) {
        card.append(el('p', 'Free models, most capable first (a workload judgement, not a provider statement)', 'field-label'));
        const order = el('ol', undefined, 'notes');
        (provider.openrouter.routing_order || []).forEach(model => order.append(el('li', String(model))));
        card.append(order);
      }
      if ((provider.openrouter.refused || []).length) {
        const refused = el('ul', undefined, 'notes');
        (provider.openrouter.refused || []).forEach(item => refused.append(el('li', String(item.model_id || 'an id') + ' — ' + String(item.reason || 'refused'))));
        card.append(el('p', 'Refused, and why (a paid id is never routed)', 'field-label'));
        card.append(refused);
      }
      card.append(el('p', 'To provide a key, run this on the machine that serves this workspace, then restart the server:', 'field-note'));
      card.append(el('pre', String(provider.set_key_command || 'python3 scripts/models.py --set-key'), 'brief-markdown'));
      card.append(el('p', 'To measure what the account can actually reach, with the key configured:', 'field-note'));
      card.append(el('pre', String(provider.probe_command || 'python3 scripts/models.py --probe-free'), 'brief-markdown'));
      card.append(el('p', String((provider.openrouter || {}).note || ''), 'field-note'));
      host.append(card);
    }
