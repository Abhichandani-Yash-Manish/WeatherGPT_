import pathlib
p = pathlib.Path('web/views.js')
t = p.read_text()
snippet = pathlib.Path('tmp/views-retrieval-snippet.js').read_text()
anchor = 'function renderActions(packet, handlers) {'
assert t.count(anchor) == 1
t = t.replace(anchor, snippet + chr(10) + anchor, 1)
old = '  body.append(renderTrace(packet));'
assert t.count(old) == 1
t = t.replace(old, '  const retrievalAccount = renderRetrievalAccount(packet);' + chr(10) + '  if (retrievalAccount) body.append(retrievalAccount);' + chr(10) + old, 1)
p.write_text(t)
print('retrieval account renderer added')