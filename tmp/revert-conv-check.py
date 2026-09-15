import pathlib
conv = pathlib.Path('tests/test_conversation_ui.js')
ct = conv.read_text()
snippet = pathlib.Path('tmp/conversation-ui-snippet.js').read_text()
assert ct.count(snippet) == 1, 'snippet present'
conv.write_text(ct.replace(snippet, '', 1))
print('reverted the misplaced check')