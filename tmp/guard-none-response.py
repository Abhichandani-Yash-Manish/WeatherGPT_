import pathlib

prov = pathlib.Path('weathergpt_data/providers.py')
p = prov.read_text()
old_ollama = """        if data.get('done_reason') == 'length':"""
assert p.count(old_ollama) == 1, p.count(old_ollama)
new_ollama = """        if not isinstance(data, dict):
            # Measured on 15 September 2026: a bare null answer crashed the planning turn.
            raise ProviderUnavailable('The local model returned no structured response. Please retry.')
        if data.get('done_reason') == 'length':"""
p = p.replace(old_ollama, new_ollama, 1)
old_open = """                        data = json.loads(response.read(400000))"""
assert p.count(old_open) == 1, p.count(old_open)
new_open = """                        data = json.loads(response.read(400000))
                        if not isinstance(data, dict) or not data.get('choices'):
                            raise ProviderUnavailable('The model provider returned no completion. Try again or switch model.')"""
p = p.replace(old_open, new_open, 1)
prov.write_text(p)

lang = pathlib.Path('weathergpt_data/language.py')
t = lang.read_text()
old_guard = """        try:
            plan=_settle_plan(request,question,now,context,recent)"""
assert t.count(old_guard) == 1, t.count(old_guard)
new_guard = """        try:
            if not isinstance(request,dict):
                # Measured on 15 September 2026: a provider that answered with a bare null
                # crashed the turn with AttributeError instead of being refused.
                raise SourceError('the model returned no plan object')
            plan=_settle_plan(request,question,now,context,recent)"""
t = t.replace(old_guard, new_guard, 1)
old_local = """            content=data.get('message',{}).get('content','')
            answer=json.loads(content)"""
assert t.count(old_local) == 1, t.count(old_local)
new_local = """            if not isinstance(data, dict):
                raise SourceError('The local model returned no structured response. Please retry.')
            content=data.get('message',{}).get('content','')
            answer=json.loads(content)"""
t = t.replace(old_local, new_local, 1)
lang.write_text(t)
print('patched')