import pathlib
p = pathlib.Path('tests/test_conversation_ui.js')
t = p.read_text()
snippet = pathlib.Path('tmp/conversation-ui-snippet.js').read_text()
anchor = "  console.log('PASS: the resolved collection point comes from the packet, or is reported absent');"
assert t.count(anchor) == 1, t.count(anchor)
t = t.replace(anchor, anchor + chr(10) + snippet, 1)
p.write_text(t)
print('inserted after the last check')