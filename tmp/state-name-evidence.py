import pathlib
p = pathlib.Path('weathergpt_data/document_ingest.py')
t = p.read_text()
start = t.index('def ingest_state(')
old = "    document = {**info, 'source_state': state, 'bytes': len(body), 'passages': passages,"
at = t.index(old, start)
insert = ("    # The state on a state target is this registry's claim until the document itself names it." + chr(10) +
          "    flat = ' '.join((page.get('text') if isinstance(page, dict) else str(page)) or '' for page in pages).lower()" + chr(10) +
          "    record['state_named_in_document'] = state.lower() in flat" + chr(10))
t = t[:at] + insert + t[at:]
p.write_text(t)
print('patched at', at)