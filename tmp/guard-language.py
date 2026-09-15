import pathlib
p = pathlib.Path('weathergpt_data/language.py')
lines = p.read_text().splitlines(keepends=True)
target = 150 - 1
assert lines[target].strip() == 'plan=_settle_plan(request,question,now,context,recent)', repr(lines[target])
indent = '            '
guard = [indent + 'if not isinstance(request,dict):' + chr(10),
         indent + '    # Measured on 15 September 2026: a provider that answered with a bare null' + chr(10),
         indent + '    # crashed the turn with AttributeError instead of being refused.' + chr(10),
         indent + '    raise SourceError(\'the model returned no plan object\')' + chr(10)]
lines[target:target] = guard
local = None
for index, line in enumerate(lines):
    if line.strip() == "content=data.get('message',{}).get('content','')":
        local = index
        break
assert local is not None
base = len(lines[local]) - len(lines[local].lstrip())
pad = ' ' * base
lines[local:local] = [pad + 'if not isinstance(data, dict):' + chr(10),
                      pad + "    raise SourceError('The local model returned no structured response. Please retry.')" + chr(10)]
p.write_text(''.join(lines))
print('patched')